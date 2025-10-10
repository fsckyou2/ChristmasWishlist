from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, WishlistItem, Purchase, WishlistChange, ProxyWishlist
from app.forms import WishlistItemForm, PurchaseForm, ProxyWishlistForm

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")


@bp.route("/my-list")
@login_required
def my_list():
    """View current user's wishlist"""
    # Only show owner's items - hide custom gifts from others
    items = (
        WishlistItem.query.filter_by(user_id=current_user.id)
        .filter((WishlistItem.added_by_id == None) | (WishlistItem.added_by_id == current_user.id))  # noqa: E711, E712
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    return render_template("wishlist/my_list.html", items=items)


@bp.route("/my-list/table")
@login_required
def my_list_table():
    """View and edit wishlist as a table"""
    # Only show owner's items - hide custom gifts from others
    items = (
        WishlistItem.query.filter_by(user_id=current_user.id)
        .filter((WishlistItem.added_by_id == None) | (WishlistItem.added_by_id == current_user.id))  # noqa: E711, E712
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    return render_template("wishlist/my_list_table.html", items=items)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_item():
    """Add item to wishlist"""
    form = WishlistItemForm()

    if form.validate_on_submit():
        item = WishlistItem(
            user_id=current_user.id,
            added_by_id=None,  # Owner-added item
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            quantity=form.quantity.data,
        )

        # Handle available_images from form (hidden field populated by scraper)
        available_images_json = request.form.get("available_images")
        if available_images_json:
            item.available_images = available_images_json

        db.session.add(item)
        db.session.flush()  # Get the item ID

        # Track the change
        change = WishlistChange(user_id=current_user.id, change_type="added", item_name=item.name, item_id=item.id)
        db.session.add(change)
        db.session.commit()

        flash("Item added to your wishlist!", "success")
        return redirect(url_for("wishlist.my_list"))

    return render_template("wishlist/add_item.html", form=form)


@bp.route("/add-custom-gift/<int:user_id>", methods=["GET", "POST"])
@login_required
def add_custom_gift(user_id):
    """Add a custom gift to another user's wishlist"""
    target_user = User.query.get_or_404(user_id)

    # Cannot add custom gifts to your own wishlist
    if target_user.id == current_user.id:
        flash("You cannot add custom gifts to your own wishlist!", "warning")
        return redirect(url_for("wishlist.my_list"))

    form = WishlistItemForm()

    if form.validate_on_submit():
        item = WishlistItem(
            user_id=target_user.id,  # For the target user's wishlist
            added_by_id=current_user.id,  # Added by current user (custom gift)
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            quantity=form.quantity.data,
        )
        db.session.add(item)
        db.session.flush()  # Get the item ID

        # Automatically claim the custom gift for the person adding it
        purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=current_user.id, quantity=item.quantity)
        db.session.add(purchase)
        db.session.commit()

        flash(
            f'Custom gift "{item.name}" added to {target_user.name}\'s wishlist and claimed by you! '
            f"They won't see it, but other users will.",
            "success",
        )
        return redirect(url_for("wishlist.view_user_list", user_id=target_user.id))

    return render_template("wishlist/add_custom_gift.html", form=form, target_user=target_user)


@bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    """Edit wishlist item"""
    item = WishlistItem.query.get_or_404(item_id)

    # Check if user owns this item OR is the person who added it as a custom gift
    is_owner = item.user_id == current_user.id
    is_custom_gift_adder = item.added_by_id == current_user.id

    if not (is_owner or is_custom_gift_adder):
        flash("You can only edit items you added.", "danger")
        return redirect(url_for("wishlist.my_list"))

    form = WishlistItemForm(obj=item)

    if form.validate_on_submit():
        item.name = form.name.data
        item.url = form.url.data
        item.description = form.description.data
        item.price = form.price.data
        item.image_url = form.image_url.data
        item.quantity = form.quantity.data

        # Handle available_images from form (hidden field populated by scraper)
        available_images_json = request.form.get("available_images")
        if available_images_json:
            item.available_images = available_images_json

        # Track the change
        change = WishlistChange(user_id=current_user.id, change_type="updated", item_name=item.name, item_id=item.id)
        db.session.add(change)
        db.session.commit()

        flash("Item updated!", "success")
        return redirect(url_for("wishlist.my_list"))

    return render_template("wishlist/edit_item.html", form=form, item=item)


@bp.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    """Delete wishlist item"""
    item = WishlistItem.query.get_or_404(item_id)

    # Check if user owns this item OR is the person who added it as a custom gift
    is_owner = item.user_id == current_user.id
    is_custom_gift_adder = item.added_by_id == current_user.id

    if not (is_owner or is_custom_gift_adder):
        flash("You can only delete items you added.", "danger")
        return redirect(url_for("wishlist.my_list"))

    # Track the change before deleting
    item_name = item.name
    wishlist_owner_id = item.user_id
    proxy_wishlist_id = item.proxy_wishlist_id
    is_custom_gift = item.is_custom_gift and item.added_by_id == current_user.id

    change = WishlistChange(
        user_id=current_user.id,
        change_type="deleted",
        item_name=item_name,
        item_id=None,  # Item will be deleted, so no ID reference
    )
    db.session.add(change)
    db.session.delete(item)
    db.session.commit()

    if is_custom_gift:
        flash("Custom gift deleted.", "success")
        # Check where the request came from via referrer
        referrer = request.referrer
        if referrer and "my-claims" in referrer:
            return redirect(url_for("wishlist.my_claims"))
        elif wishlist_owner_id:
            return redirect(url_for("wishlist.view_user_list", user_id=wishlist_owner_id))
        elif proxy_wishlist_id:
            return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=proxy_wishlist_id))
        else:
            return redirect(url_for("wishlist.all_users"))
    else:
        flash("Item deleted from your wishlist.", "success")
        return redirect(url_for("wishlist.my_list"))


@bp.route("/view/<int:user_id>")
@login_required
def view_user_list(user_id):
    """View another user's wishlist"""
    user = User.query.get_or_404(user_id)
    items = WishlistItem.query.filter_by(user_id=user_id).order_by(WishlistItem.created_at.desc()).all()
    return render_template("wishlist/view_list.html", user=user, items=items)


@bp.route("/claim/<int:item_id>", methods=["GET", "POST"])
@login_required
def claim_item(item_id):
    """Claim item to gift to another user"""
    item = WishlistItem.query.get_or_404(item_id)

    # User cannot claim their own items
    if item.user_id == current_user.id:
        flash("You cannot claim items from your own wishlist!", "warning")
        return redirect(url_for("wishlist.my_list"))

    form = PurchaseForm()

    # Set max quantity available
    remaining = item.quantity - item.total_purchased
    if remaining <= 0:
        flash("This item is already fully claimed.", "info")
        return redirect(url_for("wishlist.view_user_list", user_id=item.user_id))

    if form.validate_on_submit():
        quantity = form.quantity.data

        # Validate quantity
        if quantity > remaining:
            flash(f"Only {remaining} remaining to claim.", "warning")
        else:
            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=current_user.id, quantity=quantity)
            db.session.add(purchase)
            db.session.commit()
            flash(
                f'Claimed {quantity} of "{item.name}"! ' "Don't forget to mark it as purchased when you order it.",
                "success",
            )
            return redirect(url_for("wishlist.view_user_list", user_id=item.user_id))

    # Pre-fill with remaining quantity
    form.quantity.data = remaining

    return render_template("wishlist/claim_item.html", form=form, item=item, remaining=remaining)


# Keep old route for backward compatibility
@bp.route("/purchase/<int:item_id>", methods=["GET", "POST"])
@login_required
def purchase_item(item_id):
    """Redirect to claim_item (backward compatibility)"""
    return claim_item(item_id)


@bp.route("/unclaim/<int:purchase_id>", methods=["POST"])
@login_required
def unclaim_item(purchase_id):
    """Unclaim item"""
    purchase = Purchase.query.get_or_404(purchase_id)

    # Only the person who claimed it can unclaim it
    if purchase.purchased_by_id != current_user.id:
        flash("You can only unclaim items you claimed.", "danger")
        return redirect(url_for("wishlist.all_users"))

    item = purchase.wishlist_item
    item_name = item.name

    db.session.delete(purchase)
    db.session.commit()

    flash(f'Unclaimed "{item_name}".', "success")

    # Redirect to appropriate wishlist view
    if item.user_id:
        return redirect(url_for("wishlist.view_user_list", user_id=item.user_id))
    elif item.proxy_wishlist_id:
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=item.proxy_wishlist_id))
    else:
        return redirect(url_for("wishlist.all_users"))


# Keep old route for backward compatibility
@bp.route("/unpurchase/<int:purchase_id>", methods=["POST"])
@login_required
def unpurchase_item(purchase_id):
    """Redirect to unclaim_item (backward compatibility)"""
    return unclaim_item(purchase_id)


@bp.route("/add-empty", methods=["POST"])
@login_required
def add_empty_item():
    """Add empty item for table editing"""
    item = WishlistItem(user_id=current_user.id, added_by_id=None, name="New Item", quantity=1)
    db.session.add(item)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "item_id": item.id,
            "item": {
                "id": item.id,
                "name": item.name,
                "url": item.url or "",
                "description": item.description or "",
                "price": item.price or "",
                "quantity": item.quantity,
                "is_fully_purchased": False,
                "total_purchased": 0,
            },
        }
    )


@bp.route("/update-item/<int:item_id>", methods=["POST"])
@login_required
def update_item_quick(item_id):
    """Quick update item via AJAX"""
    item = WishlistItem.query.get_or_404(item_id)

    # Check if user owns this item OR is the person who added it as a custom gift
    is_owner = item.user_id == current_user.id
    is_custom_gift_adder = item.added_by_id == current_user.id

    if not (is_owner or is_custom_gift_adder):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    # Update fields if provided
    if "name" in data:
        item.name = data["name"]
    if "url" in data:
        item.url = data["url"]
    if "description" in data:
        item.description = data["description"]
    if "price" in data:
        item.price = float(data["price"]) if data["price"] else None
    if "quantity" in data:
        item.quantity = int(data["quantity"])
    if "image_url" in data:
        item.image_url = data["image_url"]

    # Track the change
    change = WishlistChange(user_id=current_user.id, change_type="updated", item_name=item.name, item_id=item.id)
    db.session.add(change)
    db.session.commit()

    return jsonify({"success": True})


@bp.route("/add-item-from-scraped-data", methods=["POST"])
@login_required
def add_item_from_scraped_data():
    """Add item from scraped data (used by table view's quick add URL feature)"""
    data = request.get_json()

    # Create new item with scraped data
    item = WishlistItem(
        user_id=current_user.id,
        added_by_id=None,  # Owner-added item
        name=data.get("name", "New Item"),
        url=data.get("url"),
        description=data.get("description"),
        price=float(data["price"]) if data.get("price") else None,
        image_url=data.get("image_url"),
        quantity=int(data.get("quantity", 1)),
    )

    # Handle available images
    if "images" in data and data["images"]:
        item.set_available_images(data["images"])

    db.session.add(item)
    db.session.flush()  # Get the item ID

    # Track the change
    change = WishlistChange(user_id=current_user.id, change_type="added", item_name=item.name, item_id=item.id)
    db.session.add(change)
    db.session.commit()

    return jsonify({"success": True, "item_id": item.id})


@bp.route("/all-users")
@login_required
def all_users():
    """View all users to browse their wishlists"""
    users = User.query.filter(User.id != current_user.id).order_by(User.name).all()
    proxies = ProxyWishlist.query.order_by(ProxyWishlist.name).all()
    return render_template("wishlist/all_users.html", users=users, proxies=proxies)


@bp.route("/my-claims")
@login_required
def my_claims():
    """View all items I've claimed to gift to others"""
    # Get all claims by current user with item and recipient info
    claims = Purchase.query.filter_by(purchased_by_id=current_user.id).order_by(Purchase.created_at.desc()).all()

    # Group claims by recipient (user or proxy)
    claims_by_recipient = {}
    for claim in claims:
        item = claim.wishlist_item

        # Determine if this is a user or proxy wishlist
        if item.user:
            # Regular user wishlist
            recipient_key = f"user_{item.user.id}"
            if recipient_key not in claims_by_recipient:
                claims_by_recipient[recipient_key] = {"recipient": item.user, "is_proxy": False, "claims": []}
        elif item.proxy_wishlist:
            # Proxy wishlist
            recipient_key = f"proxy_{item.proxy_wishlist.id}"
            if recipient_key not in claims_by_recipient:
                claims_by_recipient[recipient_key] = {"recipient": item.proxy_wishlist, "is_proxy": True, "claims": []}
        else:
            # Orphaned item (shouldn't happen, but handle gracefully)
            continue

        claims_by_recipient[recipient_key]["claims"].append(claim)

    return render_template("wishlist/my_claims.html", claims_by_recipient=claims_by_recipient)


@bp.route("/update-claim-status/<int:claim_id>", methods=["POST"])
@login_required
def update_claim_status(claim_id):
    """Update purchased/received/wrapped status of a claim"""
    claim = Purchase.query.get_or_404(claim_id)

    # Only the person who made the claim can update it
    if claim.purchased_by_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    if "purchased" in data:
        claim.purchased = bool(data["purchased"])
    if "received" in data:
        claim.received = bool(data["received"])
    if "wrapped" in data:
        claim.wrapped = bool(data["wrapped"])

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

        flash(f'Proxy wishlist created for "{proxy.name}"!', "success")
        return redirect(url_for("wishlist.all_users"))

    return render_template("wishlist/create_proxy_wishlist.html", form=form)


@bp.route("/view-proxy/<int:proxy_id>")
@login_required
def view_proxy_wishlist(proxy_id):
    """View a proxy wishlist"""
    proxy = ProxyWishlist.query.get_or_404(proxy_id)
    items = WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id).order_by(WishlistItem.created_at.desc()).all()
    return render_template("wishlist/view_proxy_list.html", proxy=proxy, items=items)


@bp.route("/add-to-proxy/<int:proxy_id>", methods=["GET", "POST"])
@login_required
def add_to_proxy_wishlist(proxy_id):
    """Add a custom gift to a proxy wishlist"""
    proxy = ProxyWishlist.query.get_or_404(proxy_id)

    form = WishlistItemForm()

    if form.validate_on_submit():
        item = WishlistItem(
            proxy_wishlist_id=proxy.id,  # For the proxy wishlist
            added_by_id=current_user.id,  # Added by current user (custom gift)
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            quantity=form.quantity.data,
        )
        db.session.add(item)
        db.session.flush()  # Get the item ID

        # Automatically claim the custom gift for the person adding it
        purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=current_user.id, quantity=item.quantity)
        db.session.add(purchase)
        db.session.commit()

        flash(
            f'Custom gift "{item.name}" added to {proxy.name}\'s wishlist and claimed by you!',
            "success",
        )
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=proxy.id))

    return render_template("wishlist/add_to_proxy.html", form=form, proxy=proxy)


@bp.route("/edit-proxy/<int:proxy_id>", methods=["GET", "POST"])
@login_required
def edit_proxy_wishlist(proxy_id):
    """Edit proxy wishlist name and email"""
    proxy = ProxyWishlist.query.get_or_404(proxy_id)

    # Check permissions: creator or admin
    if proxy.created_by_id != current_user.id and not current_user.is_admin:
        flash("You can only edit proxy wishlists you created.", "danger")
        return redirect(url_for("wishlist.all_users"))

    form = ProxyWishlistForm(obj=proxy)

    if form.validate_on_submit():
        proxy.name = form.name.data
        proxy.email = form.email.data.lower() if form.email.data else None
        db.session.commit()

        flash(f'Proxy wishlist for "{proxy.name}" updated!', "success")
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=proxy.id))

    return render_template("wishlist/edit_proxy.html", form=form, proxy=proxy)
