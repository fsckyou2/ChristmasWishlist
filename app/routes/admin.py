from functools import wraps

from flask import Blueprint, abort, current_app, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user

from app import db, email, policy, services
from app.forms import InviteForm, NewSeasonForm, WishlistItemForm
from app.models import User, WishlistItem, Claim, GiftHistory, Invite, ProxyWishlist, WishlistDelegate
from app.routes.auth import merge_proxy_wishlist_to_user
from app.validation import ValidationError

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You must be an administrator to access this page.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


def _visible_claims(claims):
    """Admins are protected on their own list too: hide claims on items meant for them."""
    return [
        c
        for c in claims
        if policy.can_view_claims(current_user, c.item) and not policy.is_hidden_from(current_user, c.item)
    ]


def _admin_item_or_404(item_id):
    item = db.get_or_404(WishlistItem, item_id)
    if policy.is_hidden_from(current_user, item):
        abort(404)
    return item


@bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    items = policy.visible_items(current_user, WishlistItem.query.order_by(WishlistItem.created_at.desc()).all())
    stats = {
        "total_users": User.query.count(),
        "total_items": len(items),
        "total_claims": len(_visible_claims(Claim.query.all())),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_items = items[:10]

    return render_template("admin/dashboard.html", stats=stats, recent_users=recent_users, recent_items=recent_items)


@bp.route("/users")
@login_required
@admin_required
def users():
    """View all users"""
    all_users = User.query.order_by(User.name).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/user/<int:user_id>")
@login_required
@admin_required
def view_user(user_id):
    """View user details"""
    user = db.get_or_404(User, user_id)
    wishlist_items = policy.visible_items(current_user, WishlistItem.query.filter_by(user_id=user_id).all())
    claims = _visible_claims(Claim.query.filter_by(claimed_by_id=user_id).all())

    return render_template("admin/view_user.html", user=user, wishlist_items=wishlist_items, claims=claims)


@bp.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user = db.get_or_404(User, user_id)

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        new_email = request.form.get("email", "").strip() or None  # Convert empty string to None

        if not new_name:
            flash("Name cannot be empty.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        # Validate that user has either email OR username
        if not new_email and not user.username:
            flash("User must have either an email or username.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        # Check if email is already taken by another user (if email is provided)
        if new_email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                flash("Email address is already in use.", "danger")
                return redirect(url_for("admin.edit_user", user_id=user_id))

        user.name = new_name
        user.email = new_email
        db.session.commit()

        flash("User details updated successfully.", "success")
        return redirect(url_for("admin.view_user", user_id=user_id))

    return render_template("admin/edit_user.html", user=user)


@bp.route("/user/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = db.get_or_404(User, user_id)

    # Prevent removing admin from self
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
        return redirect(url_for("admin.users"))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = "granted" if user.is_admin else "revoked"
    flash(f"Admin privileges {status} for {user.name}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = db.get_or_404(User, user_id)

    # Prevent deleting self
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.name} has been deleted.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/user/<int:user_id>/send-login-link", methods=["POST"])
@login_required
@admin_required
def send_user_login_link(user_id):
    """Send magic link login email to user"""
    user = db.get_or_404(User, user_id)

    if not user.email:
        flash(f"{user.name} does not have an email address. They must log in with username/password.", "warning")
        return redirect(url_for("admin.view_user", user_id=user_id))

    from app.email import send_magic_link_email

    success = send_magic_link_email(user)
    if success:
        flash(f"Magic link sent to {user.email}.", "success")
    else:
        flash(f"Could not send a magic link to {user.name}.", "danger")
    return redirect(url_for("admin.view_user", user_id=user_id))


@bp.route("/user/<int:user_id>/impersonate", methods=["POST"])
@login_required
@admin_required
def impersonate(user_id):
    """Impersonate a user"""
    user = db.get_or_404(User, user_id)

    # Cannot impersonate self
    if user.id == current_user.id:
        flash("You cannot impersonate yourself.", "warning")
        return redirect(url_for("admin.users"))

    # The logged-in admin stays the session's user; load_user() swaps in the target while this is set
    session["impersonate_user_id"] = user_id

    flash(f'Now impersonating {user.name}. Click "Stop impersonating" to return.', "info")
    return redirect(url_for("main.index"))


@bp.route("/stop-impersonate", methods=["POST"])
@login_required
def stop_impersonate():
    """Stop impersonating a user"""
    if session.pop("impersonate_user_id", None) is not None:
        flash("Stopped impersonating user.", "info")
    return redirect(url_for("admin.dashboard"))


@bp.route("/items")
@login_required
@admin_required
def items():
    """View all wishlist items"""
    all_items = WishlistItem.query.order_by(WishlistItem.created_at.desc()).all()
    return render_template("admin/items.html", items=policy.visible_items(current_user, all_items))


@bp.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_item(item_id):
    """Edit a wishlist item"""
    item = _admin_item_or_404(item_id)
    form = WishlistItemForm(obj=item)

    if form.validate_on_submit():
        try:
            services.update_item(item, services.item_form_data(form, request.form))
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("admin/edit_item.html", form=form, item=item)
        services.record_change(item, "updated")
        db.session.commit()

        flash(f'Item "{item.name}" has been updated.', "success")
        return redirect(url_for("admin.items"))

    return render_template("admin/edit_item.html", form=form, item=item)


@bp.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_item(item_id):
    """Delete a wishlist item"""
    item = _admin_item_or_404(item_id)
    services.delete_item(item)
    db.session.commit()
    flash(f'Item "{item.name}" has been deleted.', "success")
    return redirect(url_for("admin.items"))


@bp.route("/claims")
@login_required
@admin_required
def claims():
    """View all claims (except those on the admin's own list)"""
    all_claims = Claim.query.order_by(Claim.created_at.desc()).all()
    return render_template("admin/claims.html", claims=_visible_claims(all_claims))


@bp.route("/proxy-wishlists")
@login_required
@admin_required
def proxy_wishlists():
    """View all proxy wishlists"""
    all_proxies = ProxyWishlist.query.order_by(ProxyWishlist.created_at.desc()).all()
    return render_template("admin/proxy_wishlists.html", proxies=all_proxies)


@bp.route("/proxy-wishlist/<int:proxy_id>/merge", methods=["GET", "POST"])
@login_required
@admin_required
def merge_proxy_wishlist(proxy_id):
    """Merge a proxy wishlist into a user's account"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)

    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        if not user_id:
            flash("Please select an account to link to.", "danger")
            return redirect(url_for("admin.merge_proxy_wishlist", proxy_id=proxy_id))

        user = db.get_or_404(User, user_id)

        try:
            total_items, merged_count = merge_proxy_wishlist_to_user(proxy, user)
            db.session.commit()

            transferred_count = total_items - merged_count
            message_parts = []
            if transferred_count > 0:
                message_parts.append(f"{transferred_count} item(s) moved")
            if merged_count > 0:
                message_parts.append(f"{merged_count} item(s) combined with items already on their list")

            flash(
                f"{proxy.name}'s list is now linked to {user.name}'s account. {', '.join(message_parts)}.",
                "success",
            )
            return redirect(url_for("admin.proxy_wishlists"))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error merging proxy wishlist %s", proxy_id)
            flash("Error linking list to account; nothing was changed.", "danger")
            return redirect(url_for("admin.merge_proxy_wishlist", proxy_id=proxy_id))

    # GET request - show merge form
    all_users = User.query.order_by(User.name).all()
    items = WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id).all()
    return render_template("admin/merge_proxy_wishlist.html", proxy=proxy, users=all_users, items=items)


@bp.route("/proxy-wishlist/<int:proxy_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_proxy_wishlist(proxy_id):
    """Delete a proxy wishlist"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    proxy_name = proxy.name

    db.session.delete(proxy)
    db.session.commit()

    flash(f"{proxy_name}'s list has been deleted.", "success")
    return redirect(url_for("admin.proxy_wishlists"))


# ======================================
# Delegate Management Routes
# ======================================


@bp.route("/proxy-wishlist/<int:proxy_id>/delegates")
@login_required
@admin_required
def manage_delegates(proxy_id):
    """Manage delegates for a proxy wishlist"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    delegates = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy_id).all()

    # Get all users who could be delegates (not already delegates)
    existing_delegate_ids = [d.user_id for d in delegates]
    available_users = (
        User.query.filter(
            User.id.notin_(existing_delegate_ids), User.id != proxy.created_by_id  # Don't include creator
        )
        .order_by(User.name)
        .all()
    )

    return render_template(
        "admin/manage_delegates.html", proxy=proxy, delegates=delegates, available_users=available_users
    )


@bp.route("/proxy-wishlist/<int:proxy_id>/delegates/add", methods=["POST"])
@login_required
@admin_required
def add_delegate(proxy_id):
    """Add a delegate to a proxy wishlist"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    user_id = request.form.get("user_id", type=int)

    if not user_id:
        flash("Please select a user.", "danger")
        return redirect(url_for("admin.manage_delegates", proxy_id=proxy_id))

    user = db.get_or_404(User, user_id)

    # Check if already a delegate
    existing = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy_id, user_id=user_id).first()

    if existing:
        flash(f"{user.name} is already a helper for {proxy.name}'s list.", "warning")
        return redirect(url_for("admin.manage_delegates", proxy_id=proxy_id))

    # Create delegate
    delegate = WishlistDelegate(
        proxy_wishlist_id=proxy_id, user_id=user_id, can_add_items=True, can_edit_items=True, can_remove_items=True
    )

    db.session.add(delegate)
    db.session.commit()

    flash(f"{user.name} is now a helper for {proxy.name}'s list.", "success")
    return redirect(url_for("admin.manage_delegates", proxy_id=proxy_id))


@bp.route("/delegate/<int:delegate_id>/remove", methods=["POST"])
@login_required
@admin_required
def remove_delegate(delegate_id):
    """Remove a delegate"""
    delegate = db.get_or_404(WishlistDelegate, delegate_id)
    proxy_id = delegate.proxy_wishlist_id
    user_name = delegate.user.name
    proxy_name = delegate.proxy_wishlist.name

    db.session.delete(delegate)
    db.session.commit()

    flash(f"{user_name} is no longer a helper for {proxy_name}'s list.", "success")
    return redirect(url_for("admin.manage_delegates", proxy_id=proxy_id))


@bp.route("/delegate/<int:delegate_id>/update-permissions", methods=["POST"])
@login_required
@admin_required
def update_delegate_permissions(delegate_id):
    """Update delegate permissions"""
    delegate = db.get_or_404(WishlistDelegate, delegate_id)

    delegate.can_add_items = request.form.get("can_add_items") == "on"
    delegate.can_edit_items = request.form.get("can_edit_items") == "on"
    delegate.can_remove_items = request.form.get("can_remove_items") == "on"

    db.session.commit()

    flash(f"Helper permissions updated for {delegate.user.name}.", "success")
    return redirect(url_for("admin.manage_delegates", proxy_id=delegate.proxy_wishlist_id))


# ======================================
# Registration Invites
# ======================================


@bp.route("/invites", methods=["GET", "POST"])
@login_required
@admin_required
def invites():
    """Create and list single-use registration invites"""
    form = InviteForm()
    new_invite_url = None
    if form.validate_on_submit():
        invite, token = Invite.create(created_by=current_user, note=form.note.data, days=form.days.data)
        db.session.commit()
        # Shown once: only a hash of the token is stored
        new_invite_url = f"{current_app.config['APP_URL']}{url_for('auth.register', invite=token)}"
        form = InviteForm(formdata=None)

    all_invites = Invite.query.order_by(Invite.created_at.desc()).all()
    return render_template("admin/invites.html", form=form, invites=all_invites, new_invite_url=new_invite_url)


@bp.route("/invites/<int:invite_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke_invite(invite_id):
    invite = db.get_or_404(Invite, invite_id)
    if invite.used_at is None:
        invite.revoked = True
        db.session.commit()
        flash("Invite revoked.", "success")
    return redirect(url_for("admin.invites"))


# ======================================
# Seasons
# ======================================


@bp.route("/season", methods=["GET", "POST"])
@login_required
@admin_required
def new_season():
    """Close the past season: archive given gifts into everyone's history and clear them from the lists"""
    form = NewSeasonForm()
    if request.method == "GET":
        form.season.data = services.default_season_label()

    if form.validate_on_submit():
        season = form.season.data.strip()
        christmas = services.next_christmas(season)
        stats = services.close_season(season)
        db.session.commit()
        if not form.notify.data:
            email_note = ""
        elif email.delivery_enabled():
            email_note = f" Emailed {email.send_season_open_email(christmas)} people that lists are open."
        else:
            email.send_season_open_email(christmas)  # renders and logs only
            email_note = (
                f" Email delivery is off, so nothing was sent; the preview below is what "
                f"{len(email.season_open_recipients())} people would have received."
            )
        flash(
            f"Christmas {season} is wrapped up: all {stats['total_items']} item(s) archived and cleared "
            f"({stats['claimed_items']} claimed, {stats['unclaimed_items']} not claimed). "
            f"Welcome to Christmas {christmas}!" + email_note,
            "success",
        )
        return redirect(url_for("admin.new_season"))

    past = (
        db.session.query(GiftHistory.season, db.func.count(GiftHistory.id))
        .group_by(GiftHistory.season)
        .order_by(GiftHistory.season.desc())
        .all()
    )
    upcoming = services.next_christmas(services.default_season_label())
    if form.season.data and str(form.season.data).strip().isdigit():
        upcoming = services.next_christmas(form.season.data)
    subject, text, _ = email.render_season_open_email(current_user, upcoming)
    return render_template(
        "admin/season.html",
        form=form,
        preview=services.season_preview(),
        past=past,
        email_preview={"subject": subject, "text": text, "to": current_user.email},
        email_recipients=len(email.season_open_recipients()),
        mail_delivery=email.delivery_enabled(),
    )
