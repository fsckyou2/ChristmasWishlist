"""Wishlist item operations shared by the HTML views, the JSON endpoints, the delegate views and registration.

Routes check permissions (app.policy) and then call these; these functions validate input (app.validation) and keep
the daily-digest change log honest.
"""

import json
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from app import db, policy
from app.models import Claim, DeletedItem, GiftHistory, ProxyWishlist, User, WishlistChange, WishlistItem, utcnow
from app.validation import clean_item_fields

_ITEM_FIELDS = (
    "name",
    "url",
    "description",
    "price",
    "image_url",
    "quantity",
    "available_images",
    "size",
    "color",
    "most_wanted",
)


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


def similar_claimed_items(item, viewer):
    """Items on the same list that look like `item` and that somebody is already getting.

    Warns a giver before they commit to a second copy. A surprise gift and the same thing added later by
    the recipient are two separate items, and nothing else notices: adding never combines them, and the
    recipient can't see claims on their own list, so without this nobody finds out until two arrive.

    Only items `viewer` may see are considered, so this can never reveal a surprise that is hidden from
    them (a helper on someone's list, for instance, doesn't see other people's surprise gifts).
    """
    if item.user_id is not None:
        on_same_list = WishlistItem.user_id == item.user_id
    else:
        on_same_list = WishlistItem.proxy_wishlist_id == item.proxy_wishlist_id
    others = WishlistItem.query.filter(on_same_list, WishlistItem.id != item.id).all()
    return [
        other
        for other in others
        if other.claims and not policy.is_hidden_from(viewer, other) and similar_items(item, other)
    ]


def _top_position(list_filter):
    """A position that puts a new item at the top of its list's chosen order."""
    lowest = db.session.query(db.func.min(WishlistItem.position)).filter(list_filter).scalar()
    return (lowest if lowest is not None else 1) - 1


def reorder(items_in_order):
    """Save the owner's drag-to-reorder order."""
    for index, item in enumerate(items_in_order):
        item.position = index


def record_change(item, change_type):
    """Log a change for the daily digest, attributed to the list owner.

    Only changes to items on a user's own list that the owner can see are logged. Custom gifts (someone else's
    surprise for the owner) and proxy-list items are never logged, so the digest can't reveal them.
    """
    if item.user_id is None or item.added_by_id not in (None, item.user_id):
        return None
    change = WishlistChange(
        user_id=item.user_id,
        change_type=change_type,
        item_name=item.name,
        item_id=None if change_type == "deleted" else item.id,
    )
    db.session.add(change)
    return change


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
    """The owner adds an item to their own list. It is never combined with anything already there.

    Deliberately does no duplicate matching. A name/URL likeness can't tell two variants of one product
    apart (`similar_items` doesn't look at `size` or `color`), and `merge_items` is destructive with no
    undo, so a wrong guess silently discarded what the owner had just typed. Combining two entries is a
    thing people ask for on purpose: `wishlist.merge_items_manual`, which checks permissions first.
    """
    item = create_item(data, user_id=user.id)
    item.position = _top_position(WishlistItem.user_id == user.id)
    record_change(item, "added")
    return item


def add_custom_gift(giver, data, *, user_id=None, proxy_wishlist_id=None):
    """Someone adds a surprise gift to another person's list; it is claimed by them automatically."""
    item = create_item(data, user_id=user_id, proxy_wishlist_id=proxy_wishlist_id, added_by_id=giver.id)
    db.session.add(Claim(item=item, claimed_by_id=giver.id, quantity=item.quantity))
    return item


# Deleting an item keeps a snapshot (with its claims) for a short while so the person who deleted it can Undo.
UNDO_WINDOW = timedelta(minutes=30)
_SNAPSHOT_FIELDS = (
    "user_id",
    "proxy_wishlist_id",
    "added_by_id",
    "name",
    "url",
    "description",
    "price",
    "image_url",
    "available_images",
    "quantity",
    "most_wanted",
    "size",
    "color",
    "position",
)
_CLAIM_FIELDS = ("claimed_by_id", "quantity", "purchased", "received", "wrapped")


def _stamp(value):
    return value.isoformat() if value else None


def delete_item(item, deleted_by=None):
    """Delete `item` (claims cascade). With `deleted_by`, keep an undo snapshot and return it (else None)."""
    change = record_change(item, "deleted")
    snapshot = None
    if deleted_by is not None:
        db.session.flush()
        payload = {field: getattr(item, field) for field in _SNAPSHOT_FIELDS}
        payload["created_at"] = _stamp(item.created_at)
        payload["claims"] = [
            {**{field: getattr(c, field) for field in _CLAIM_FIELDS}, "created_at": _stamp(c.created_at)}
            for c in item.claims
        ]
        snapshot = DeletedItem(
            payload=json.dumps(payload), deleted_by_id=deleted_by.id, change_id=change.id if change else None
        )
        db.session.add(snapshot)
        DeletedItem.query.filter(DeletedItem.deleted_at < utcnow() - timedelta(days=1)).delete()
    db.session.delete(item)
    if snapshot is not None:
        db.session.flush()
    return snapshot


def undo_delete(snapshot, user):
    """Put a deleted item (and its claims) back. Returns the item, or None if it's too late or not theirs.

    Claims come back as they were, so nobody's "I'll get this" is lost and the owner sees exactly what they saw.
    """
    if snapshot.deleted_by_id != user.id or snapshot.deleted_at < utcnow() - UNDO_WINDOW:
        return None
    data = json.loads(snapshot.payload)
    if data["user_id"] and db.session.get(User, data["user_id"]) is None:
        return None
    if data["proxy_wishlist_id"] and db.session.get(ProxyWishlist, data["proxy_wishlist_id"]) is None:
        return None
    item = WishlistItem(**{field: data.get(field) for field in _SNAPSHOT_FIELDS})
    if data.get("created_at"):
        item.created_at = datetime.fromisoformat(data["created_at"])
    db.session.add(item)
    db.session.flush()
    for claim in data["claims"]:
        if db.session.get(User, claim["claimed_by_id"]) is None:
            continue
        restored = Claim(wishlist_item_id=item.id, **{field: claim[field] for field in _CLAIM_FIELDS})
        if claim.get("created_at"):
            restored.created_at = datetime.fromisoformat(claim["created_at"])
        db.session.add(restored)

    # The digest: if "Removed" hasn't gone out yet, forget it; if it has, announce the item again
    change = db.session.get(WishlistChange, snapshot.change_id) if snapshot.change_id else None
    if change is not None and not change.notified:
        db.session.delete(change)
    elif snapshot.change_id:
        record_change(item, "added")
    db.session.delete(snapshot)
    return item


def item_form_data(form, request_form):
    """Collect item fields from a WishlistItemForm plus the image picker's hidden field."""
    data = {field: getattr(form, field).data for field in _ITEM_FIELDS if hasattr(form, field)}
    if request_form.get("available_images"):  # absent/empty: keep the item's existing image choices
        data["available_images"] = request_form.get("available_images")
    return data


# --- Seasons -------------------------------------------------------------------------------------------------------


def default_season_label(now=None):
    """The Christmas being closed: last year's, unless we're already past this year's."""
    now = now or utcnow()
    return str(now.year if (now.month, now.day) >= (12, 26) else now.year - 1)


def next_christmas(season):
    """The Christmas that starts when `season` is closed ("2025" -> 2026)."""
    return int(season) + 1


def season_preview():
    """Counts of what close_season() would do. No item names, so it can't spoil anyone (including the admin)."""
    items = WishlistItem.query.all()
    claimed = [i for i in items if i.claims]
    return {
        "total_items": len(items),
        "claimed_items": len(claimed),
        "unclaimed_items": len(items) - len(claimed),
        "claims": sum(len(i.claims) for i in claimed),
        "lists": len({(i.user_id, i.proxy_wishlist_id) for i in items}),
    }


def close_season(season):
    """Start fresh: archive every item on every list, then clear them all.

    - Every item, claimed or not, is saved to gift_history (a silent record, not shown on the site): what was wished
      for, how many, how many were claimed, and by whom.
    - Then every item is removed along with all claims. Lists themselves (including lists for someone and their
      helpers) stay.
    - No WishlistChange rows are written, so this never shows up in the daily digest.
    Returns the same counts as season_preview(). The caller commits.
    """
    stats = season_preview()
    for item in WishlistItem.query.all():
        givers = ", ".join(dict.fromkeys(c.claimed_by.name for c in item.claims if c.claimed_by))
        db.session.add(
            GiftHistory(
                season=season,
                recipient_user_id=item.user_id,
                recipient_proxy_id=item.proxy_wishlist_id,
                recipient_name=item.user.name if item.user else item.proxy_wishlist.name,
                item_name=item.name,
                url=item.url,
                image_url=item.image_url,
                price=item.price,
                quantity=item.quantity or 1,
                claimed_quantity=min(item.total_claimed, item.quantity or 1),
                givers=givers[:500] or None,
                was_surprise=item.is_custom_gift,
            )
        )
        db.session.delete(item)  # claims cascade
    db.session.flush()
    return stats
