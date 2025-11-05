from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, WishlistItem, Purchase, WishlistChange, ProxyWishlist, WishlistDelegate
from app.forms import WishlistItemForm, PurchaseForm, ProxyWishlistForm
from difflib import SequenceMatcher

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")


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
    """Merge new_item into existing_item, preserving the best data from both."""
    # Merge data: prefer new_item's data if existing is missing
    if new_item.description and not existing_item.description:
        existing_item.description = new_item.description
    if new_item.price and not existing_item.price:
        existing_item.price = new_item.price
    if new_item.image_url and not existing_item.image_url:
        existing_item.image_url = new_item.image_url
    if new_item.url and not existing_item.url:
        existing_item.url = new_item.url

    # Use the higher quantity
    if new_item.quantity > existing_item.quantity:
        existing_item.quantity = new_item.quantity

    # Transfer any purchases from new_item to existing_item
    purchases = Purchase.query.filter_by(wishlist_item_id=new_item.id).all()
    for purchase in purchases:
        purchase.wishlist_item_id = existing_item.id

    # Flush the purchase updates before deleting the item to ensure they're persisted
    if purchases:
        db.session.flush()

    # Delete the new item since we've merged everything
    db.session.delete(new_item)

    return existing_item


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

        # Check for duplicate items against ALL items (including hidden custom gifts)
        all_user_items = WishlistItem.query.filter_by(user_id=current_user.id).filter(WishlistItem.id != item.id).all()
        merged = False

        for existing_item in all_user_items:
            if similar_items(item, existing_item):
                # Check if existing_item is a custom gift from someone else
                is_custom_gift_from_other = existing_item.added_by_id and existing_item.added_by_id != current_user.id

                if is_custom_gift_from_other:
                    # Merge custom gift INTO the new item (keep new item, delete custom gift)
                    merge_items(item, existing_item)
                    flash(
                        "Item added to your wishlist!",
                        "success",
                    )
                else:
                    # Both are user's own items - merge new INTO existing (keep existing, delete new)
                    merge_items(existing_item, item)
                    flash(
                        f'Item merged with existing item "{existing_item.name}" in your wishlist!',
                        "info",
                    )

                merged = True
                db.session.commit()
                return redirect(url_for("wishlist.my_list"))

        if not merged:
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

    # Check permissions:
    # - Owner can edit their own items (but not custom gifts added by others)
    # - Custom gift adder can edit custom gifts they added
    # - Admin can edit any item
    is_owner_item = item.user_id == current_user.id and (
        item.added_by_id is None or item.added_by_id == current_user.id
    )  # noqa: E711
    is_custom_gift_adder = item.added_by_id == current_user.id
    is_admin = current_user.is_admin

    if not (is_owner_item or is_custom_gift_adder or is_admin):
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

    # Check permissions (same as edit):
    # - Owner can delete their own items (but not custom gifts added by others)
    # - Custom gift adder can delete custom gifts they added
    # - Admin can delete any item
    is_owner_item = item.user_id == current_user.id and (
        item.added_by_id is None or item.added_by_id == current_user.id
    )  # noqa: E711
    is_custom_gift_adder = item.added_by_id == current_user.id
    is_admin = current_user.is_admin

    if not (is_owner_item or is_custom_gift_adder or is_admin):
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
    if item.user_id and item.user_id == current_user.id:
        flash("You cannot claim items from your own wishlist!", "warning")
        return redirect(url_for("wishlist.my_list"))

    form = PurchaseForm()

    # Set max quantity available
    remaining = item.quantity - item.total_purchased
    if remaining <= 0:
        flash("This item is already fully claimed.", "info")
        if item.proxy_wishlist_id:
            return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=item.proxy_wishlist_id))
        else:
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
            if item.proxy_wishlist_id:
                return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=item.proxy_wishlist_id))
            else:
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

    # Redirect back to the wishlist being viewed
    if item.proxy_wishlist_id:
        return redirect(url_for("wishlist.view_proxy_wishlist", proxy_id=item.proxy_wishlist_id))
    elif item.user_id:
        return redirect(url_for("wishlist.view_user_list", user_id=item.user_id))
    else:
        # Fallback to My Gifts for Others if we can't determine the wishlist
        return redirect(url_for("wishlist.my_claims"))


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

    # Check permissions (same as edit):
    # - Owner can update their own items (but not custom gifts added by others)
    # - Custom gift adder can update custom gifts they added
    # - Admin can update any item
    is_owner_item = item.user_id == current_user.id and (
        item.added_by_id is None or item.added_by_id == current_user.id
    )  # noqa: E711
    is_custom_gift_adder = item.added_by_id == current_user.id
    is_admin = current_user.is_admin

    if not (is_owner_item or is_custom_gift_adder or is_admin):
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

    # Check for duplicate items against ALL items (including hidden custom gifts)
    all_user_items = WishlistItem.query.filter_by(user_id=current_user.id).filter(WishlistItem.id != item.id).all()

    for existing_item in all_user_items:
        if similar_items(item, existing_item):
            # Check if existing_item is a custom gift from someone else
            is_custom_gift_from_other = existing_item.added_by_id and existing_item.added_by_id != current_user.id

            if is_custom_gift_from_other:
                # Merge custom gift INTO the new item (keep new item, delete custom gift)
                merge_items(item, existing_item)
                db.session.commit()
                return jsonify(
                    {
                        "success": True,
                        "merged": True,
                        "merged_with_id": item.id,
                        "message": "Item added!",
                    }
                )
            else:
                # Both are user's own items - merge new INTO existing (keep existing, delete new)
                merge_items(existing_item, item)
                db.session.commit()
                return jsonify(
                    {
                        "success": True,
                        "merged": True,
                        "merged_with_id": existing_item.id,
                        "message": f'Item merged with existing item "{existing_item.name}"',
                    }
                )

    # No duplicates found - track the change and add normally
    change = WishlistChange(user_id=current_user.id, change_type="added", item_name=item.name, item_id=item.id)
    db.session.add(change)
    db.session.commit()

    return jsonify({"success": True, "item_id": item.id, "merged": False})


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


@bp.route("/merge-items", methods=["POST"])
@login_required
def merge_items_manual():
    """Manually merge two items - used when user selects 'Merge with...' in the UI"""
    data = request.get_json()
    source_item_id = data.get("source_item_id")  # Item to be merged (will be deleted)
    target_item_id = data.get("target_item_id")  # Item to merge into (will be kept)

    if not source_item_id or not target_item_id:
        return jsonify({"error": "Missing item IDs"}), 400

    source_item = WishlistItem.query.get_or_404(source_item_id)
    target_item = WishlistItem.query.get_or_404(target_item_id)

    # Verify both items belong to the same user or proxy
    if source_item.user_id != target_item.user_id or source_item.proxy_wishlist_id != target_item.proxy_wishlist_id:
        return jsonify({"error": "Items must belong to the same wishlist"}), 403

    # Any authenticated user viewing a wishlist can merge items they can see
    # (Wishlist owners can't see custom gifts on their own list anyway, so this is safe)

    # Perform the merge
    try:
        merge_items(target_item, source_item)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f'Item merged with "{target_item.name}"',
                "target_item_id": target_item.id,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =====================================================
# Delegate Routes - Manage Proxy Wishlists as Delegate
# =====================================================


@bp.route("/delegate-wishlists")
@login_required
def delegate_wishlists():
    """View all proxy wishlists that current user is a delegate for"""
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
    """View and manage a proxy wishlist as a delegate (can't see claims)"""
    proxy = ProxyWishlist.query.get_or_404(proxy_id)

    # Check if user is a delegate
    if not proxy.can_manage(current_user):
        flash("You don't have permission to manage this wishlist.", "danger")
        return redirect(url_for("wishlist.all_users"))

    # Get delegate permissions
    delegate_record = None
    if not current_user.is_admin and current_user.id != proxy.created_by_id:
        delegate_record = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy.id, user_id=current_user.id).first()

    # Get items (delegates can see all items, but not who claimed them)
    items = WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id).order_by(WishlistItem.created_at.desc()).all()

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
    proxy = ProxyWishlist.query.get_or_404(proxy_id)

    # Check if user can manage and add items
    if not proxy.can_manage(current_user):
        flash("You don't have permission to add items to this wishlist.", "danger")
        return redirect(url_for("wishlist.all_users"))

    # Check delegate permissions
    if not current_user.is_admin and current_user.id != proxy.created_by_id:
        delegate = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy.id, user_id=current_user.id).first()

        if not delegate or not delegate.can_add_items:
            flash("You don't have permission to add items.", "danger")
            return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy_id))

    form = WishlistItemForm()

    if form.validate_on_submit():
        item = WishlistItem(
            proxy_wishlist_id=proxy.id,
            added_by_id=current_user.id,  # Track who added it
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            quantity=form.quantity.data,
        )

        # Handle available_images from form
        available_images_json = request.form.get("available_images")
        if available_images_json:
            item.available_images = available_images_json

        db.session.add(item)
        db.session.commit()

        flash(f'Item "{item.name}" added to {proxy.name}\'s wishlist!', "success")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    return render_template("wishlist/delegate_add_item.html", form=form, proxy=proxy)


@bp.route("/delegate/edit-item/<int:item_id>", methods=["GET", "POST"])
@login_required
def delegate_edit_item(item_id):
    """Edit item on proxy wishlist as a delegate"""
    item = WishlistItem.query.get_or_404(item_id)

    if not item.proxy_wishlist:
        flash("This item doesn't belong to a proxy wishlist.", "danger")
        return redirect(url_for("wishlist.my_list"))

    proxy = item.proxy_wishlist

    # Check if user can manage and edit items
    if not proxy.can_manage(current_user):
        flash("You don't have permission to edit items on this wishlist.", "danger")
        return redirect(url_for("wishlist.all_users"))

    # Check delegate permissions
    if not current_user.is_admin and current_user.id != proxy.created_by_id:
        delegate = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy.id, user_id=current_user.id).first()

        if not delegate or not delegate.can_edit_items:
            flash("You don't have permission to edit items.", "danger")
            return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    form = WishlistItemForm(obj=item)

    if form.validate_on_submit():
        item.name = form.name.data
        item.url = form.url.data
        item.description = form.description.data
        item.price = form.price.data
        item.image_url = form.image_url.data
        item.quantity = form.quantity.data

        db.session.commit()

        flash(f'Item "{item.name}" updated!', "success")
        return redirect(url_for("wishlist.manage_as_delegate", proxy_id=proxy.id))

    return render_template("wishlist/delegate_edit_item.html", form=form, item=item, proxy=proxy)


@bp.route("/delegate/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delegate_delete_item(item_id):
    """Delete item from proxy wishlist as a delegate"""
    item = WishlistItem.query.get_or_404(item_id)

    if not item.proxy_wishlist:
        return jsonify({"error": "This item doesn't belong to a proxy wishlist"}), 400

    proxy = item.proxy_wishlist

    # Check if user can manage and remove items
    if not proxy.can_manage(current_user):
        return jsonify({"error": "You don't have permission to delete items from this wishlist"}), 403

    # Check delegate permissions
    if not current_user.is_admin and current_user.id != proxy.created_by_id:
        delegate = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy.id, user_id=current_user.id).first()

        if not delegate or not delegate.can_remove_items:
            return jsonify({"error": "You don't have permission to remove items"}), 403

    db.session.delete(item)
    db.session.commit()

    return jsonify({"success": True, "message": f'Item "{item.name}" deleted'})
