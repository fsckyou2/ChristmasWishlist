from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from difflib import SequenceMatcher
from app import db
from app.models import User, ProxyWishlist, WishlistItem, Purchase
from app.forms import RegistrationForm, LoginForm
from app.email import send_magic_link_email, send_welcome_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


def similar_items(item1, item2, threshold=0.9):
    """
    Check if two items are similar enough to merge.
    Returns True if URLs match or names are >90% similar.
    """
    # Exact URL match (ignore case and trailing slashes)
    if item1.url and item2.url:
        url1 = item1.url.lower().rstrip("/")
        url2 = item2.url.lower().rstrip("/")
        if url1 == url2:
            return True

    # Fuzzy name matching
    if item1.name and item2.name:
        similarity = SequenceMatcher(None, item1.name.lower(), item2.name.lower()).ratio()
        if similarity >= threshold:
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

    # Delete the new_item
    db.session.delete(new_item)
    return existing_item


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Passwordless user registration"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user_email = form.email.data.lower()
        user = User(email=user_email, name=form.name.data)
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

            total_items = len(items_to_transfer) + merged_count
            merge_msg = f" ({merged_count} duplicate(s) merged)" if merged_count > 0 else ""
            flash(
                f"Welcome! We found a wishlist created for you with {total_items} item(s){merge_msg}. "
                "It's now been added to your account!",
                "success",
            )

        db.session.commit()

        # Send welcome email with login link included
        send_welcome_email(user)

        flash("Registration successful! Check your email for a welcome message with your login link.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Passwordless login - sends magic link"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            send_magic_link_email(user)
        # Always show success message to prevent email enumeration
        flash("If an account exists with that email, a login link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/login.html", form=form)


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
