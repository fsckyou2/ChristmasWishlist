from datetime import timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db, limiter, policy, services
from app.forms import ClaimForm, ProxyWishlistForm, WishlistItemForm
from app.models import (
    Claim,
    DeletedItem,
    ListVisit,
    ProxyWishlist,
    Reminder,
    User,
    WishlistDelegate,
    WishlistItem,
    list_order,
    utcnow,
)
from app.validation import ValidationError

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")

# One "please add to your wishlist" email per person per this long, whoever sends it
REMINDER_COOLDOWN = timedelta(days=3)


def _list_url(item, anchor=False):
    """Where to send someone after acting on `item` (optionally scrolled back to its card)."""
    if item.proxy_wishlist_id:
        url = url_for("wishlist.view_proxy_wishlist", proxy_id=item.proxy_wishlist_id)
    elif item.user_id and item.user_id != current_user.id:
        url = url_for("wishlist.view_user_list", user_id=item.user_id)
    else:
        return url_for("wishlist.my_list")
    return f"{url}#item-{item.id}" if anchor else url


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


def _own_items():
    items = list_order(WishlistItem.query.filter_by(user_id=current_user.id)).all()
    return policy.visible_items(current_user, items)


def flash_deleted(snapshot, what):
    """'Deleted "X".' with an Undo button (base.html renders the "undo" category)."""
    flash({"text": f"{what}.", "undo_url": url_for("wishlist.undo_delete", deleted_id=snapshot.id)}, "undo")


def _flash_form_errors(form):
    for errors in form.errors.values():
        for error in errors:
            flash(error, "danger")


@bp.route("/my-list")
@login_required
def my_list():
    """My Wishlist: add from a link, edit in place, Most wanted, reorder (custom gifts from others are hidden)"""
    return render_template("wishlist/my_list.html", items=_own_items())


@bp.route("/my-list/table")
@login_required
def my_list_table():
    """The old table view; My Wishlist now edits in place."""
    return redirect(url_for("wishlist.my_list"), code=301)


@bp.route("/reorder", methods=["POST"])
@login_required
def reorder_items():
    """Save the order of My Wishlist. Must list exactly the items the owner can see (hidden gifts stay put)."""
    ids = _json_body().get("item_ids")
    if not isinstance(ids, list) or not all(type(i) is int for i in ids) or len(set(ids)) != len(ids):
        return jsonify({"error": "Couldn't save the order. Refresh and try again."}), 400
    mine = {item.id: item for item in _own_items()}
    if set(ids) != set(mine):
        return jsonify({"error": "Your list changed. Refresh and try again."}), 409
    services.reorder([mine[i] for i in ids])
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_item():
    """Add item to wishlist"""
    form = WishlistItemForm()
    if form.validate_on_submit():
        try:
            item, merged = services.add_own_item(current_user, services.item_form_data(form, request.form))
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/add_item.html", form=form)
        db.session.commit()
        if merged:
            flash(f'Combined with "{item.name}", which was already on your list.', "info")
        else:
            flash("Item added to My Wishlist.", "success")
        return redirect(url_for("wishlist.my_list"))
    return render_template("wishlist/add_item.html", form=form)


@bp.route("/add-custom-gift/<int:user_id>", methods=["GET", "POST"])
@login_required
def add_custom_gift(user_id):
    """Add a custom gift to another user's wishlist"""
    target_user = db.get_or_404(User, user_id)
    if target_user.id == current_user.id:
        flash("You can't add a surprise gift to your own list.", "warning")
        return redirect(url_for("wishlist.my_list"))

    form = WishlistItemForm()
    if form.validate_on_submit():
        try:
            item = services.add_custom_gift(
                current_user, services.item_form_data(form, request.form), user_id=target_user.id
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/add_custom_gift.html", form=form, target_user=target_user)
        db.session.commit()
        flash(
            f'Surprise gift "{item.name}" added for {target_user.name}. It\'s hidden from {target_user.name}.',
            "success",
        )
        return redirect(url_for("wishlist.view_user_list", user_id=target_user.id))

    return render_template("wishlist/add_custom_gift.html", form=form, target_user=target_user)


@bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    """Edit an item (owner, the custom-gift adder, or an admin; never a gift hidden from you)"""
    item = db.get_or_404(WishlistItem, item_id)
    if policy.is_hidden_from(current_user, item):
        abort(404)
    if not policy.can_edit_item(current_user, item):
        flash("You can only edit items you added.", "danger")
        return redirect(url_for("wishlist.my_list"))

    form = WishlistItemForm(obj=item)
    if form.validate_on_submit():
        try:
            services.update_item(item, services.item_form_data(form, request.form))
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/edit_item.html", form=form, item=item)
        services.record_change(item, "updated")
        db.session.commit()
        flash("Item updated!", "success")
        return redirect(_list_url(item))

    return render_template("wishlist/edit_item.html", form=form, item=item)


@bp.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    """Delete an item (same rules as editing)"""
    item = db.get_or_404(WishlistItem, item_id)
    if policy.is_hidden_from(current_user, item):
        abort(404)
    if not policy.can_delete_item(current_user, item):
        flash("You can only delete items you added.", "danger")
        return redirect(url_for("wishlist.my_list"))

    is_custom_gift = item.is_custom_gift and item.added_by_id == current_user.id
    destination = _list_url(item)
    name = item.name
    snapshot = services.delete_item(item, deleted_by=current_user)
    db.session.commit()

    if is_custom_gift:
        flash_deleted(snapshot, f'Deleted surprise gift "{name}"')
        if request.form.get("next") == "my_claims":
            return redirect(url_for("wishlist.my_claims"))
        return redirect(destination)
    flash_deleted(snapshot, f'Deleted "{name}" from My Wishlist')
    return redirect(url_for("wishlist.my_list"))


@bp.route("/undo-delete/<int:deleted_id>", methods=["POST"])
@login_required
def undo_delete(deleted_id):
    """Undo a delete you just made (for a little while)"""
    snapshot = db.session.get(DeletedItem, deleted_id)
    item = services.undo_delete(snapshot, current_user) if snapshot else None
    back = request.referrer if (request.referrer or "").startswith(request.host_url) else None
    if item is None:
        flash("Too late to undo that one. Add the item again if you need it.", "warning")
        return redirect(back or url_for("wishlist.my_list"))
    db.session.commit()
    flash(f'"{item.name}" is back.', "success")
    return redirect(back or _list_url(item, anchor=True))


@bp.route("/view/<int:user_id>")
@login_required
def view_user_list(user_id):
    """View another user's wishlist, with claims. Your own list redirects to the claim-free view."""
    user = db.get_or_404(User, user_id)
    if not policy.can_view_user_list(current_user, user):
        return redirect(url_for("wishlist.my_list"))
    items = list_order(WishlistItem.query.filter_by(user_id=user_id)).all()
    ListVisit.touch(current_user, list_user_id=user.id)
    db.session.commit()
    return render_template("wishlist/view_list.html", user=user, items=items)


@bp.route("/claim/<int:item_id>", methods=["GET", "POST"])
@login_required
def claim_item(item_id):
    """Claim an item to give"""
    item = db.get_or_404(WishlistItem, item_id)
    if policy.is_hidden_from(current_user, item):
        abort(404)
    if not policy.can_claim(current_user, item):
        flash("You can't get items from your own list.", "warning")
        return redirect(url_for("wishlist.my_list"))

    remaining = item.remaining_quantity
    if remaining <= 0:
        flash("Everything on this item is already claimed.", "info")
        return redirect(_list_url(item))

    form = ClaimForm()
    if form.validate_on_submit():
        quantity = form.quantity.data
        if quantity > remaining:
            flash(f"Only {remaining} left.", "warning")
        else:
            db.session.add(Claim(item=item, claimed_by_id=current_user.id, quantity=quantity))
            db.session.commit()
            what = f'"{item.name}"' if quantity == 1 else f'{quantity} of "{item.name}"'
            flash(
                f"You're getting {what}. It's on Gifts I'm Giving; tap Undo on the item if you change your mind.",
                "success",
            )
            return redirect(_list_url(item, anchor=True))

    form.quantity.data = remaining
    return render_template("wishlist/claim_item.html", form=form, item=item, remaining=remaining)


@bp.route("/unclaim/<int:claim_id>", methods=["POST"])
@login_required
def unclaim_item(claim_id):
    """Unclaim an item you claimed"""
    claim = db.get_or_404(Claim, claim_id)
    if claim.claimed_by_id != current_user.id:
        flash("You can only undo gifts you're getting.", "danger")
        return redirect(url_for("wishlist.all_users"))

    item = claim.item
    db.session.delete(claim)
    db.session.commit()
    flash(f'Undone: you\'re no longer getting "{item.name}".', "success")
    if request.form.get("next") == "my_claims":
        return redirect(url_for("wishlist.my_claims"))
    return redirect(_list_url(item, anchor=True))


@bp.route("/update-item/<int:item_id>", methods=["POST"])
@login_required
def update_item_quick(item_id):
    """Edit in place / ★ Most wanted on My Wishlist (JSON)"""
    item = db.get_or_404(WishlistItem, item_id)
    if policy.is_hidden_from(current_user, item):
        abort(404)
    if not policy.can_edit_item(current_user, item):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        services.update_item(item, _json_body(), partial=True)
    except ValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    services.record_change(item, "updated")
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/add-item-from-scraped-data", methods=["POST"])
@login_required
def add_item_from_scraped_data():
    """My Wishlist's "Add from a link" (JSON)"""
    data = _json_body()
    fields = {key: data.get(key) for key in ("name", "url", "description", "price", "image_url") if key in data}
    fields.setdefault("name", "New Item")
    fields["quantity"] = data.get("quantity", 1)
    if data.get("images"):
        fields["available_images"] = data["images"]

    try:
        item, merged = services.add_own_item(current_user, fields)
    except ValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    db.session.commit()

    if merged:
        return jsonify(
            {
                "success": True,
                "merged": True,
                "merged_with_id": item.id,
                "message": f'Combined with "{item.name}".',
            }
        )
    # Same response whether or not a hidden surprise was folded into this item
    return jsonify({"success": True, "item_id": item.id, "merged": False})


def _browse_summary(items, visit, owner_id=None):
    """Counts for one row of Browse Wishlists, from the items this viewer can see on that list."""
    since = visit.last_seen_at if visit else None
    return {
        "total": len(items),
        "available": sum(1 for item in items if item.remaining_quantity > 0),
        "new": sum(
            1
            for item in items
            if since and item.created_at and item.created_at > since and item.added_by_id != current_user.id
        ),
        # Nothing the person added themselves yet (surprise gifts from others don't count)
        "empty": owner_id is not None and not any(item.added_by_id in (None, owner_id) for item in items),
    }


def _recent_reminder(user_id):
    return (
        Reminder.query.filter(Reminder.recipient_id == user_id, Reminder.sent_at > utcnow() - REMINDER_COOLDOWN)
        .order_by(Reminder.sent_at.desc())
        .first()
    )


@bp.route("/all-users")
@login_required
def all_users():
    """Browse Wishlists: everyone's list with how much is still available and what's new since you last looked"""
    users = User.query.filter(User.id != current_user.id).order_by(User.name).all()
    proxies = ProxyWishlist.query.order_by(ProxyWishlist.name).all()
    visits = ListVisit.query.filter_by(viewer_id=current_user.id).all()
    user_visits = {v.list_user_id: v for v in visits if v.list_user_id}
    proxy_visits = {v.list_proxy_id: v for v in visits if v.list_proxy_id}
    summaries = {
        ("user", u.id): _browse_summary(u.wishlist_items.all(), user_visits.get(u.id), owner_id=u.id) for u in users
    }
    for p in proxies:
        summaries[("proxy", p.id)] = _browse_summary(
            policy.visible_items(current_user, p.items), proxy_visits.get(p.id)
        )
    reminders = {u.id: _recent_reminder(u.id) for u in users if summaries[("user", u.id)]["empty"]}
    return render_template(
        "wishlist/all_users.html", users=users, proxies=proxies, summaries=summaries, reminders=reminders
    )


@bp.route("/remind/<int:user_id>", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def remind(user_id):
    """Email someone whose wishlist is still empty (at most once every few days, whoever asks)"""
    from app.email import send_reminder_email

    user = db.get_or_404(User, user_id)
    back = url_for("wishlist.all_users")
    items = user.wishlist_items.all()
    if user.id == current_user.id or not user.email or not _browse_summary(items, None, owner_id=user.id)["empty"]:
        flash(f"No reminder needed for {user.name}.", "info")
        return redirect(back)
    if _recent_reminder(user.id):
        flash(f"{user.name} was reminded recently. Give them a few days.", "info")
        return redirect(back)
    if not send_reminder_email(current_user, user):
        flash("Email is turned off right now, so no reminder was sent.", "warning")
        return redirect(back)
    db.session.add(Reminder(sender_id=current_user.id, recipient_id=user.id))
    db.session.commit()
    flash(f"Reminder sent to {user.name}.", "success")
    return redirect(back)


@bp.route("/my-claims")
@login_required
def my_claims():
    """Everything I've claimed to give, grouped by recipient"""
    claims = Claim.query.filter_by(claimed_by_id=current_user.id).order_by(Claim.created_at.desc()).all()

    claims_by_recipient = {}
    for claim in claims:
        item = claim.item
        if item.user:
            key, recipient, is_proxy = f"user_{item.user.id}", item.user, False
        elif item.proxy_wishlist:
            key, recipient, is_proxy = f"proxy_{item.proxy_wishlist.id}", item.proxy_wishlist, True
        else:
            continue
        claims_by_recipient.setdefault(key, {"recipient": recipient, "is_proxy": is_proxy, "claims": []})
        claims_by_recipient[key]["claims"].append(claim)

    for data in claims_by_recipient.values():
        data.update(_giving_summary(data["claims"]))
    overall = _giving_summary([c for data in claims_by_recipient.values() for c in data["claims"]])
    return render_template("wishlist/my_claims.html", claims_by_recipient=claims_by_recipient, overall=overall)


def _giving_summary(claims):
    """Spend (price x quantity) and progress: to buy (not bought yet), to wrap (bought, not wrapped), done (wrapped)."""
    return {
        "gifts": len(claims),
        "spend": sum(c.item.price * c.quantity for c in claims if c.item.price),
        "unpriced": sum(1 for c in claims if not c.item.price),
        "to_buy": sum(1 for c in claims if not c.wrapped and not c.purchased),
        "to_wrap": sum(1 for c in claims if not c.wrapped and c.purchased),
        "done": sum(1 for c in claims if c.wrapped),
    }


@bp.route("/update-claim-status/<int:claim_id>", methods=["POST"])
@login_required
def update_claim_status(claim_id):
    """Update purchased/received/wrapped status of a claim"""
    claim = db.get_or_404(Claim, claim_id)
    if claim.claimed_by_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = _json_body()
    for field in ("purchased", "received", "wrapped"):
        if field in data:
            setattr(claim, field, bool(data[field]))
    db.session.commit()
    return jsonify(
        {"success": True, "purchased": claim.purchased, "received": claim.received, "wrapped": claim.wrapped}
    )


@bp.route("/create-proxy-wishlist", methods=["GET", "POST"])
@login_required
def create_proxy_wishlist():
    """Create a wishlist for someone who doesn't have an account yet"""
    form = ProxyWishlistForm()
    if form.validate_on_submit():
        proxy = ProxyWishlist(
            name=form.name.data,
            email=form.email.data.lower() if form.email.data else None,
            created_by_id=current_user.id,
        )
        db.session.add(proxy)
        db.session.commit()
        flash(f'Started a list for "{proxy.name}".', "success")
        return redirect(url_for("wishlist.all_users"))
    return render_template("wishlist/create_proxy_wishlist.html", form=form)


@bp.route("/view-proxy/<int:proxy_id>")
@login_required
def view_proxy_wishlist(proxy_id):
    """View a proxy wishlist. Delegates stand in for the owner, so other people's custom gifts are hidden."""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    items = list_order(WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id)).all()
    is_helper = proxy.is_delegate(current_user)
    ListVisit.touch(current_user, list_proxy_id=proxy.id)
    db.session.commit()
    return render_template(
        "wishlist/view_proxy_list.html",
        proxy=proxy,
        items=policy.visible_items(current_user, items),
        is_helper=is_helper,
        show_claimers=not is_helper,  # policy.can_view_claimers: helpers see that it's claimed, not by whom
    )


@bp.route("/add-to-proxy/<int:proxy_id>", methods=["GET", "POST"])
@login_required
def add_to_proxy_wishlist(proxy_id):
    """Add a custom gift to a proxy wishlist"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    form = WishlistItemForm()
    if form.validate_on_submit():
        try:
            item = services.add_custom_gift(
                current_user, services.item_form_data(form, request.form), proxy_wishlist_id=proxy.id
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/add_to_proxy.html", form=form, proxy=proxy)
        db.session.commit()
        flash(f'Surprise gift "{item.name}" added for {proxy.name}. It\'s hidden from {proxy.name}.', "success")
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=proxy.id))
    return render_template("wishlist/add_to_proxy.html", form=form, proxy=proxy)


@bp.route("/edit-proxy/<int:proxy_id>", methods=["GET", "POST"])
@login_required
def edit_proxy_wishlist(proxy_id):
    """Edit proxy wishlist name and email (creator or admin)"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    if proxy.created_by_id != current_user.id and not current_user.is_admin:
        flash("You can only edit lists you started.", "danger")
        return redirect(url_for("wishlist.all_users"))

    form = ProxyWishlistForm(obj=proxy)
    if form.validate_on_submit():
        proxy.name = form.name.data
        proxy.email = form.email.data.lower() if form.email.data else None
        db.session.commit()
        flash(f'"{proxy.name}"\'s list details updated.', "success")
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=proxy.id))
    return render_template("wishlist/edit_proxy.html", form=form, proxy=proxy)


@bp.route("/merge-items", methods=["POST"])
@login_required
def merge_items_manual():
    """Merge one item into another on the same list ("Merge with..." on a custom gift).

    Merging deletes the source item, so you must be allowed to delete it, and you must be able to see the target.
    """
    data = _json_body()
    source_id, target_id = _int_or_none(data.get("source_item_id")), _int_or_none(data.get("target_item_id"))
    if source_id is None or target_id is None:
        return jsonify({"error": "Missing item IDs"}), 400
    source_item = db.session.get(WishlistItem, source_id)
    target_item = db.session.get(WishlistItem, target_id)
    if source_item is None or target_item is None:
        return jsonify({"error": "Item not found"}), 404
    if policy.is_hidden_from(current_user, source_item) or policy.is_hidden_from(current_user, target_item):
        return jsonify({"error": "Item not found"}), 404
    if not policy.can_merge(current_user, source_item, target_item):
        return jsonify({"error": "You can only combine items you added with items on the same list."}), 403

    services.merge_items(target_item, source_item)
    db.session.commit()
    return jsonify(
        {"success": True, "message": f'Combined with "{target_item.name}".', "target_item_id": target_item.id}
    )


# =====================================================
# Delegate Routes - Manage Proxy Wishlists as Delegate
# =====================================================


@bp.route("/delegate-wishlists")
@login_required
def delegate_wishlists():
    """All proxy wishlists the current user is a delegate for"""
    delegated_lists = (
        ProxyWishlist.query.join(WishlistDelegate)
        .filter(WishlistDelegate.user_id == current_user.id)
        .order_by(ProxyWishlist.name)
        .all()
    )
    return render_template("wishlist/delegate_wishlists.html", delegated_lists=delegated_lists)


@bp.route("/manage-delegate/<int:proxy_id>")
@login_required
def manage_as_delegate(proxy_id):
    """Manage a proxy wishlist as its creator, an admin or a delegate (no claims, no others' custom gifts)"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    if not proxy.can_manage(current_user):
        flash("You don't have permission to help with this list.", "danger")
        return redirect(url_for("wishlist.all_users"))

    delegate_record = None
    if not current_user.is_admin and current_user.id != proxy.created_by_id:
        delegate_record = proxy.delegate_record(current_user)

    all_items = list_order(WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id)).all()
    items = [item for item in all_items if not item.is_custom_gift or item.added_by_id == current_user.id]

    return render_template(
        "wishlist/manage_delegate.html",
        proxy=proxy,
        items=items,
        delegate_record=delegate_record,
        is_delegate=delegate_record is not None,
    )


@bp.route("/delegate/add-item/<int:proxy_id>", methods=["GET", "POST"])
@login_required
def delegate_add_item(proxy_id):
    """Add item to proxy wishlist as a delegate"""
    proxy = db.get_or_404(ProxyWishlist, proxy_id)
    if not proxy.can_manage(current_user):
        flash("You don't have permission to help with this list.", "danger")
        return redirect(url_for("wishlist.all_users"))
    if not policy.delegate_permission(current_user, proxy, "add"):
        flash("You don't have permission to add items.", "danger")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy_id))

    form = WishlistItemForm()
    if form.validate_on_submit():
        try:
            item = services.create_item(
                services.item_form_data(form, request.form), proxy_wishlist_id=proxy.id, added_by_id=current_user.id
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/delegate_add_item.html", form=form, proxy=proxy)
        db.session.commit()
        flash(f'Item "{item.name}" added to {proxy.name}\'s Wishlist.', "success")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    return render_template("wishlist/delegate_add_item.html", form=form, proxy=proxy)


@bp.route("/delegate/edit-item/<int:item_id>", methods=["GET", "POST"])
@login_required
def delegate_edit_item(item_id):
    """Edit item on proxy wishlist as a delegate"""
    item = db.get_or_404(WishlistItem, item_id)
    if not item.proxy_wishlist:
        flash("This item isn't on a list for someone.", "danger")
        return redirect(url_for("wishlist.my_list"))

    proxy = item.proxy_wishlist
    if not proxy.can_manage(current_user):
        flash("You don't have permission to help with this list.", "danger")
        return redirect(url_for("wishlist.all_users"))
    if policy.is_hidden_from(current_user, item):
        abort(404)
    if not policy.delegate_permission(current_user, proxy, "edit"):
        flash("You don't have permission to edit items.", "danger")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    form = WishlistItemForm(obj=item)
    if form.validate_on_submit():
        try:
            services.update_item(item, services.item_form_data(form, request.form))
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("wishlist/delegate_edit_item.html", form=form, item=item, proxy=proxy)
        db.session.commit()
        flash(f'Item "{item.name}" updated!', "success")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    return render_template("wishlist/delegate_edit_item.html", form=form, item=item, proxy=proxy)


@bp.route("/delegate/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delegate_delete_item(item_id):
    """Delete item from proxy wishlist as a delegate"""
    item = db.get_or_404(WishlistItem, item_id)
    if not item.proxy_wishlist:
        return jsonify({"error": "This item isn't on a list for someone."}), 400

    proxy = item.proxy_wishlist
    if not proxy.can_manage(current_user):
        return jsonify({"error": "You don't have permission to help with this list."}), 403
    if policy.is_hidden_from(current_user, item):
        return jsonify({"error": "Item not found"}), 404
    if not policy.delegate_permission(current_user, proxy, "remove"):
        return jsonify({"error": "You don't have permission to remove items"}), 403

    name = item.name
    snapshot = services.delete_item(item, deleted_by=current_user)
    db.session.commit()
    flash_deleted(snapshot, f'Deleted "{name}" from {proxy.name}\'s Wishlist')  # shown when the page reloads
    return jsonify({"success": True, "message": f'Deleted "{name}"'})
