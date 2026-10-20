"""Wishlist item operations shared by the HTML views, the JSON endpoints, the delegate views and registration.

Routes check permissions (app.policy) and then call these; these functions validate input (app.validation) and keep
the daily-digest change log honest.
"""

from difflib import SequenceMatcher

from app import db
from app.models import Claim, WishlistChange, WishlistItem
from app.validation import clean_item_fields

_ITEM_FIELDS = ("name", "url", "description", "price", "image_url", "quantity", "available_images")


def _significant_words(name):
    return {w.lower() for w in name.replace(",", "").replace("–", " ").replace("-", " ").split() if len(w) >= 4}


def similar_items(item1, item2, threshold=0.75):
    """Check if two items are similar enough to merge."""
    # Exact URL match (most reliable)
    if item1.url and item2.url and item1.url.lower().rstrip("/") == item2.url.lower().rstrip("/"):
        return True

    if not (item1.name and item2.name):
        return False

    # Name similarity
    if SequenceMatcher(None, item1.name.lower(), item2.name.lower()).ratio() >= threshold:
        return True

    # Significant word overlap: share 40% of 4+ letter words, and at least 3 of them
    words1, words2 = _significant_words(item1.name), _significant_words(item2.name)
    if words1 and words2:
        intersection = words1 & words2
        jaccard = len(intersection) / len(words1 | words2)
        if jaccard >= 0.4 and len(intersection) >= 3:
            return True
    return False


def merge_items(existing_item, new_item):
    """Merge new_item into existing_item (filling gaps, taking the larger quantity), move its claims, delete it."""
    for field in ("description", "price", "image_url", "url"):
        if getattr(new_item, field) and not getattr(existing_item, field):
            setattr(existing_item, field, getattr(new_item, field))
    existing_item.quantity = max(existing_item.quantity or 1, new_item.quantity or 1)

    for claim in list(new_item.claims):
        claim.item = existing_item
    db.session.flush()
    db.session.delete(new_item)
    return existing_item


def record_change(item, change_type):
    """Log a change for the daily digest, attributed to the list owner.

    Only changes to items on a user's own list that the owner can see are logged. Custom gifts (someone else's
    surprise for the owner) and proxy-list items are never logged, so the digest can't reveal them.
    """
    if item.user_id is None or item.added_by_id not in (None, item.user_id):
        return
    db.session.add(
        WishlistChange(
            user_id=item.user_id,
            change_type=change_type,
            item_name=item.name,
            item_id=None if change_type == "deleted" else item.id,
        )
    )


def create_item(data, *, user_id=None, proxy_wishlist_id=None, added_by_id=None):
    """Validate `data` and add a new item. Raises app.validation.ValidationError on bad input."""
    fields = clean_item_fields(data)
    item = WishlistItem(user_id=user_id, proxy_wishlist_id=proxy_wishlist_id, added_by_id=added_by_id, **fields)
    db.session.add(item)
    db.session.flush()
    return item


def update_item(item, data, partial=False):
    """Validate `data` and apply it to `item`. Raises app.validation.ValidationError on bad input."""
    fields = clean_item_fields(data, partial=partial)
    for field, value in fields.items():
        setattr(item, field, value)
    return item


def add_own_item(user, data):
    """The owner adds an item to their own list, merging with their own visible duplicates.

    A similar *hidden* custom gift is folded into the new item, so its giver's claim carries over (and nobody else
    buys it twice). The owner gets the same response either way, so it doesn't reveal the surprise.

    Returns (item, merged_into_existing_visible_item).
    """
    item = create_item(data, user_id=user.id)
    others = WishlistItem.query.filter(WishlistItem.user_id == user.id, WishlistItem.id != item.id).all()
    for existing in others:
        if not similar_items(item, existing):
            continue
        if existing.added_by_id not in (None, user.id):
            merge_items(item, existing)
            break
        merge_items(existing, item)
        record_change(existing, "updated")
        return existing, True
    record_change(item, "added")
    return item, False


def add_custom_gift(giver, data, *, user_id=None, proxy_wishlist_id=None):
    """Someone adds a surprise gift to another person's list; it is claimed by them automatically."""
    item = create_item(data, user_id=user_id, proxy_wishlist_id=proxy_wishlist_id, added_by_id=giver.id)
    db.session.add(Claim(item=item, claimed_by_id=giver.id, quantity=item.quantity))
    return item


def delete_item(item):
    record_change(item, "deleted")
    db.session.delete(item)


def item_form_data(form, request_form):
    """Collect item fields from a WishlistItemForm plus the image picker's hidden field."""
    data = {field: getattr(form, field).data for field in _ITEM_FIELDS if hasattr(form, field)}
    if request_form.get("available_images"):  # absent/empty: keep the item's existing image choices
        data["available_images"] = request_form.get("available_images")
    return data
