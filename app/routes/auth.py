from flask import Blueprint, render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm

from app import db, limiter
from app.models import Invite, User, ProxyWishlist, WishlistItem
from app.forms import (
    RegistrationForm,
    LoginForm,
    UsernamePasswordRegistrationForm,
    UsernamePasswordLoginForm,
    AccountSettingsForm,
    ChangePasswordForm,
)
from app.email import send_magic_link_email, send_welcome_email
from app.services import merge_items, similar_items

bp = Blueprint("auth", __name__, url_prefix="/auth")

AUTH_LIMIT = "10 per minute;60 per hour"


def _email_rate_key():
    return "magic:" + (request.form.get("email") or "").strip().lower()


def _invite_from_session():
    """The invite this browser is registering with, if it is still usable."""
    return Invite.find_usable(session.get("invite_token"))


def _finish_registration(user, invite):
    invite.mark_used(user)
    session.pop("invite_token", None)


def names_match(proxy_name, user_name):
    """
    Check if a proxy wishlist name matches a user's name.

    Matches if:
    - Exact match (case-insensitive)
    - User name contains the proxy name (e.g., "Westley Welch" contains "Westley")
    - Proxy name contains the user name (e.g., "Westley" contains "West")

    Args:
        proxy_name: Name from ProxyWishlist
        user_name: Name from User

    Returns:
        bool: True if names match
    """
    if not proxy_name or not user_name:
        return False

    proxy_lower = proxy_name.lower().strip()
    user_lower = user_name.lower().strip()

    # Exact match
    if proxy_lower == user_lower:
        return True

    # Check if user name contains proxy name (e.g., "Westley Welch" contains "Westley")
    if proxy_lower in user_lower:
        return True

    # Check if proxy name contains user name (e.g., "Westley" contains "West")
    if user_lower in proxy_lower:
        return True

    # Check if first word matches (common nickname/full name pattern)
    proxy_first = proxy_lower.split()[0] if proxy_lower.split() else ""
    user_first = user_lower.split()[0] if user_lower.split() else ""

    if proxy_first and user_first:
        # Match if one is contained in the other (e.g., "West" in "Westley")
        if proxy_first in user_first or user_first in proxy_first:
            return True

    return False


def merge_proxy_wishlist_to_user(proxy, user):
    """
    Merge a proxy wishlist into a user's account.

    For each proxy item:
    - If similar to existing user item: merge proxy item into existing item
    - If no match: transfer proxy item to user's wishlist as custom gift

    Returns tuple: (total_items_transferred, items_merged_count)
    """
    # Get all items from proxy wishlist
    proxy_items = WishlistItem.query.filter_by(proxy_wishlist_id=proxy.id).all()

    # Get existing items the user might already have
    existing_items = WishlistItem.query.filter_by(user_id=user.id).all()

    total_items = len(proxy_items)
    merged_count = 0

    # Process each proxy item - check for duplicates and merge if needed
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
            # No match found - transfer to user's wishlist as custom gift
            proxy_item.proxy_wishlist_id = None
            proxy_item.user_id = user.id
            # Keep added_by_id to preserve who added custom gifts

    # Delete the proxy wishlist
    db.session.delete(proxy)

    return total_items, merged_count


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit(AUTH_LIMIT, methods=["POST"])
def register():
    """Registration is by invitation only. Shows both registration options once a valid invite is presented."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    token = request.args.get("invite")
    if token:
        # Remember the invite and drop it from the URL so it doesn't linger in history or Referer headers
        if Invite.find_usable(token):
            session["invite_token"] = token
        else:
            session.pop("invite_token", None)
            flash("That invite link is invalid, expired, or already used.", "danger")
        return redirect(url_for("auth.register"))

    invite = _invite_from_session()
    if invite is None:
        return render_template("auth/invite_required.html"), 403

    email_form = RegistrationForm()
    password_form = UsernamePasswordRegistrationForm()

    # Handle email registration form submission
    if email_form.validate_on_submit() and email_form.submit.data:
        user_email = email_form.email.data.lower()
        user = User(email=user_email, name=email_form.name.data)
        db.session.add(user)
        db.session.flush()  # Get the user ID before committing

        # Check for proxy wishlists with matching email OR matching name
        proxies_to_merge = []

        # First, check for email match (most specific)
        proxy_by_email = ProxyWishlist.query.filter_by(email=user_email).first()
        if proxy_by_email:
            proxies_to_merge.append(proxy_by_email)

        # Then, check for name matches (may find additional proxies)
        all_proxies = ProxyWishlist.query.all()
        for proxy in all_proxies:
            if proxy not in proxies_to_merge and names_match(proxy.name, user.name):
                proxies_to_merge.append(proxy)

        # Merge all matching proxy wishlists
        for proxy in proxies_to_merge:
            merge_proxy_wishlist_to_user(proxy, user)

        _finish_registration(user, invite)
        db.session.commit()

        # Send welcome email with login link included
        send_welcome_email(user)

        flash("Registration successful! Check your email for a welcome message with your login link.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/unified_register.html", email_form=email_form, password_form=password_form)


@bp.route("/register-username", methods=["GET", "POST"])
@limiter.limit(AUTH_LIMIT, methods=["POST"])
def register_username():
    """Username/password registration (also invite-only)"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    invite = _invite_from_session()
    if invite is None:
        return render_template("auth/invite_required.html"), 403

    form = UsernamePasswordRegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.lower(), name=form.name.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Get the user ID before committing

        # Check for proxy wishlists with matching name
        proxies_to_merge = []
        all_proxies = ProxyWishlist.query.all()
        for proxy in all_proxies:
            if names_match(proxy.name, user.name):
                proxies_to_merge.append(proxy)

        # Merge all matching proxy wishlists
        for proxy in proxies_to_merge:
            merge_proxy_wishlist_to_user(proxy, user)

        _finish_registration(user, invite)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login_username"))

    return render_template("auth/register_username.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(AUTH_LIMIT, methods=["POST"])
@limiter.limit("5 per hour", methods=["POST"], key_func=_email_rate_key)
def login():
    """Unified login page showing all auth options"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    email_form = LoginForm()
    password_form = UsernamePasswordLoginForm()

    if email_form.validate_on_submit() and email_form.submit.data:
        user = User.query.filter_by(email=email_form.email.data.lower()).first()
        if user:
            send_magic_link_email(user)
        # Always show success message to prevent email enumeration
        flash("If an account exists with that email, a login link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/unified_auth.html", email_form=email_form, password_form=password_form)


@bp.route("/login-username", methods=["GET", "POST"])
@limiter.limit(AUTH_LIMIT, methods=["POST"])
def login_username():
    """Username/password login"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = UsernamePasswordLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user and user.check_password(form.password.data):
            session.clear()
            user.record_login()
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome, {user.name}!", "success")
            return redirect(url_for("main.index"))
        flash("Invalid username or password.", "danger")

    return render_template("auth/login_username.html", form=form)


@bp.route("/magic-login/<token>", methods=["GET", "POST"])
@limiter.limit(AUTH_LIMIT, methods=["POST"])
def magic_login(token):
    """Magic link login. GET only shows a confirm button, so email link scanners can't use up the link."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_magic_link_token(token)
    if not user:
        flash("Invalid or expired login link (each link works once). Request a new one below.", "danger")
        return redirect(url_for("auth.login"))

    form = FlaskForm()
    if form.validate_on_submit():
        session.clear()
        user.record_login()
        db.session.commit()
        login_user(user)
        flash(f"Welcome, {user.name}!", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/magic_confirm.html", form=form, user=user)


@bp.route("/logout", methods=["POST"])
def logout():
    """Log out, or stop impersonating if an admin is impersonating someone"""
    if "impersonate_user_id" in session:
        session.pop("impersonate_user_id")
        flash("Stopped impersonating user.", "info")
        return redirect(url_for("admin.dashboard"))
    logout_user()
    session.clear()
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
