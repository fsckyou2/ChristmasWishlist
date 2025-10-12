from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from difflib import SequenceMatcher
from app import db
from app.models import User, ProxyWishlist, WishlistItem, Purchase
from app.forms import (
    RegistrationForm,
    LoginForm,
    UsernamePasswordRegistrationForm,
    UsernamePasswordLoginForm,
    AccountSettingsForm,
    ChangePasswordForm,
)
from app.email import send_magic_link_email, send_welcome_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


def similar_items(item1, item2, threshold=0.75):
    """Check if two items are similar enough to merge."""
    # Method 1: Exact URL match (most reliable)
    if item1.url and item2.url:
        url1 = item1.url.lower().rstrip("/")
        url2 = item2.url.lower().rstrip("/")
        if url1 == url2:
            return True

    # Method 2: Name similarity using SequenceMatcher
    if item1.name and item2.name:
        name_similarity = SequenceMatcher(None, item1.name.lower(), item2.name.lower()).ratio()
        if name_similarity >= threshold:
            return True

        # Method 3: Significant word overlap (for products with different descriptions)
        # Extract words of meaningful length (4+ characters)
        words1 = set(
            [w.lower() for w in item1.name.replace(",", "").replace("–", " ").replace("-", " ").split() if len(w) >= 4]
        )
        words2 = set(
            [w.lower() for w in item2.name.replace(",", "").replace("–", " ").replace("-", " ").split() if len(w) >= 4]
        )

        if words1 and words2:
            # Calculate Jaccard similarity (intersection over union)
            intersection = words1 & words2
            union = words1 | words2
            jaccard = len(intersection) / len(union) if union else 0

            # If they share 40% of significant words, likely the same item
            # AND they share at least 3 words, it's probably the same product
            if jaccard >= 0.4 and len(intersection) >= 3:
                return True

    return False


def merge_items(existing_item, new_item):
    """
    Merge new_item into existing_item, preserving the best data from both.
    Transfers purchases and deletes the new_item.
    """
    # Preserve the better data (prefer non-null values from new_item if existing_item lacks them)
    if new_item.description and not existing_item.description:
        existing_item.description = new_item.description
    if new_item.price and not existing_item.price:
        existing_item.price = new_item.price
    if new_item.image_url and not existing_item.image_url:
        existing_item.image_url = new_item.image_url
    if new_item.url and not existing_item.url:
        existing_item.url = new_item.url

    # Merge quantities (take the max)
    if new_item.quantity > existing_item.quantity:
        existing_item.quantity = new_item.quantity

    # Transfer all purchases from new_item to existing_item
    purchases = Purchase.query.filter_by(wishlist_item_id=new_item.id).all()
    for purchase in purchases:
        purchase.wishlist_item_id = existing_item.id

    # Flush the purchase updates before deleting the item to ensure they're persisted
    if purchases:
        db.session.flush()

    # Delete the new_item
    db.session.delete(new_item)
    return existing_item


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Unified registration page showing all registration options"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    email_form = RegistrationForm()
    password_form = UsernamePasswordRegistrationForm()

    # Handle email registration form submission
    if email_form.validate_on_submit() and email_form.submit.data:
        user_email = email_form.email.data.lower()
        user = User(email=user_email, name=email_form.name.data)
        db.session.add(user)
        db.session.flush()  # Get the user ID before committing

        # Check for proxy wishlists with matching email
        proxy = ProxyWishlist.query.filter_by(email=user_email).first()
        merged_count = 0
        if proxy:
            # Get all items from proxy wishlist
            proxy_items = WishlistItem.query.filter_by(proxy_wishlist_id=proxy.id).all()

            # Get existing items the user might already have (shouldn't happen on first registration, but be safe)
            existing_items = WishlistItem.query.filter_by(user_id=user.id).all()

            # Process each proxy item - check for duplicates and merge if needed
            items_to_transfer = []
            for proxy_item in proxy_items:
                # Check if this item should be merged with an existing item
                merged = False
                for existing_item in existing_items:
                    if similar_items(proxy_item, existing_item):
                        # Merge proxy_item into existing_item
                        merge_items(existing_item, proxy_item)
                        merged = True
                        merged_count += 1
                        break

                if not merged:
                    # No match found - transfer to user's wishlist
                    proxy_item.proxy_wishlist_id = None
                    proxy_item.user_id = user.id
                    # Keep added_by_id to preserve who added custom gifts
                    items_to_transfer.append(proxy_item)

            # Delete the proxy wishlist
            db.session.delete(proxy)

        db.session.commit()

        # Send welcome email with login link included
        send_welcome_email(user)

        flash("Registration successful! Check your email for a welcome message with your login link.", "success")
        return redirect(url_for("auth.login"))

    # Show unified registration page
    return render_template("auth/unified_register.html", email_form=email_form, password_form=password_form)


@bp.route("/register-username", methods=["GET", "POST"])
def register_username():
    """Username/password registration"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = UsernamePasswordRegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.lower(), name=form.name.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login_username"))

    return render_template("auth/register_username.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Unified login page showing all auth options"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    email_form = LoginForm()
    password_form = UsernamePasswordLoginForm()

    # Handle email form submission
    if email_form.validate_on_submit() and email_form.submit.data:
        user = User.query.filter_by(email=email_form.email.data.lower()).first()
        if user:
            send_magic_link_email(user)
        # Always show success message to prevent email enumeration
        flash("If an account exists with that email, a login link has been sent.", "info")
        return redirect(url_for("auth.login"))

    # Handle password form submission (via separate route for clarity)
    # This GET request shows the unified auth page

    return render_template("auth/unified_auth.html", email_form=email_form, password_form=password_form)


@bp.route("/login-username", methods=["GET", "POST"])
def login_username():
    """Username/password login"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = UsernamePasswordLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome, {user.name}!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("auth/login_username.html", form=form)


@bp.route("/magic-login/<token>")
def magic_login(token):
    """Login via magic link"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_magic_link_token(token)
    if not user:
        flash("Invalid or expired login link.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    flash(f"Welcome, {user.name}!", "success")
    return redirect(url_for("main.index"))


@bp.route("/logout")
def logout():
    """User logout"""
    # Clear impersonation if active
    if "impersonate_user_id" in session:
        session.pop("impersonate_user_id")
        flash("Stopped impersonating user.", "info")
    else:
        logout_user()
        flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@bp.route("/complete-tour", methods=["POST"])
@login_required
def complete_tour():
    """Mark user's tour as completed"""
    current_user.has_seen_tour = True
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Account settings page"""
    account_form = AccountSettingsForm()
    password_form = ChangePasswordForm()

    # Pre-populate account form
    if account_form.validate_on_submit():
        # Update account info
        current_user.name = account_form.name.data

        # Handle email update
        new_email = account_form.email.data.lower() if account_form.email.data else None
        if new_email and new_email != current_user.email:
            # Check if email is already taken
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != current_user.id:
                flash("Email already in use by another account.", "danger")
            else:
                current_user.email = new_email
                flash("Email updated successfully!", "success")

        # Handle username update
        new_username = account_form.username.data.lower() if account_form.username.data else None
        if new_username and new_username != current_user.username:
            # Check if username is already taken
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != current_user.id:
                flash("Username already taken.", "danger")
            else:
                current_user.username = new_username
                flash("Username updated successfully!", "success")

        # Validate that user has either email OR username
        if not current_user.email and not current_user.username:
            flash("You must have either an email or username.", "danger")
        else:
            db.session.commit()
            flash("Account updated successfully!", "success")
            return redirect(url_for("auth.settings"))

    elif password_form.validate_on_submit() and password_form.submit.data:
        # Handle password change
        # If user already has a password, verify current password
        if current_user.password_hash:
            if not password_form.current_password.data:
                flash("Current password is required.", "danger")
            elif not current_user.check_password(password_form.current_password.data):
                flash("Current password is incorrect.", "danger")
            else:
                current_user.set_password(password_form.new_password.data)
                db.session.commit()
                flash("Password changed successfully!", "success")
                return redirect(url_for("auth.settings"))
        else:
            # User doesn't have a password yet, set it
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password set successfully! You can now log in with your username/password.", "success")
            return redirect(url_for("auth.settings"))

    # Pre-populate form with current values
    if not account_form.is_submitted():
        account_form.name.data = current_user.name
        account_form.email.data = current_user.email
        account_form.username.data = current_user.username

    return render_template("auth/settings.html", account_form=account_form, password_form=password_form)
