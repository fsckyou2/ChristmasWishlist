"""Authorization and surprise-protection rules, in one place.

The core invariant: a person never learns what others are giving them. On their own list they cannot see claims,
claimers, or custom gifts that someone else added, anywhere (pages, JSON responses, emails, admin pages).

Proxy wishlists belong to someone without an account. Their delegates ("helpers") manage the list, so other
people's custom gifts are hidden from them. They see *that* items are claimed (so they don't buy something twice)
but not *who* claimed them.

Admins can manage everything except that they are also protected on their own list. While impersonating, the
impersonated user *is* current_user, so the admin sees exactly what that user would.
"""


def owns_list_of(user, item):
    """True if the item is on the user's own (non-proxy) list."""
    return user is not None and item.user_id is not None and item.user_id == user.id


def stands_in_for_owner(user, item):
    """True if the user is the list owner, or a delegate of the proxy wishlist the item is on."""
    if owns_list_of(user, item):
        return True
    return item.proxy_wishlist_id is not None and item.proxy_wishlist.is_delegate(user)


def is_hidden_from(user, item):
    """Custom gifts are invisible to the list owner (and to proxy delegates), except ones they added themselves."""
    if not stands_in_for_owner(user, item):
        return False
    if item.proxy_wishlist_id is not None:
        return item.is_custom_gift and item.added_by_id != user.id
    return item.added_by_id is not None and item.added_by_id != user.id


def visible_items(user, items):
    return [item for item in items if not is_hidden_from(user, item)]


def can_view_claims(user, item):
    """Claim status and claimer names are never shown to the person the gift is for."""
    return not owns_list_of(user, item)


def can_view_claimers(user, item):
    """Who claimed an item. Hidden from the list owner (as with all claim info) and from the helpers of a list kept
    for someone: helpers still see *that* an item is claimed, so they don't buy it twice, but not by whom."""
    if not can_view_claims(user, item):
        return False
    return not (item.proxy_wishlist_id is not None and item.proxy_wishlist.is_delegate(user))


def can_view_user_list(viewer, list_owner):
    """The 'browse' view of a user's list shows claims, so it is for everyone except the owner."""
    return viewer.id != list_owner.id


def can_edit_item(user, item):
    if user is None or is_hidden_from(user, item):
        return False
    if owns_list_of(user, item) and item.added_by_id in (None, user.id):
        return True
    if item.added_by_id is not None and item.added_by_id == user.id:
        return True  # custom gift adder, or the delegate who added a proxy item
    return bool(user.is_admin)


can_delete_item = can_edit_item


def can_claim(user, item):
    return user is not None and not owns_list_of(user, item) and not is_hidden_from(user, item)


def can_merge(user, source, target):
    """Merging deletes `source`, so the caller must be allowed to delete it and to see `target`."""
    if source.id == target.id:
        return False
    if (source.user_id, source.proxy_wishlist_id) != (target.user_id, target.proxy_wishlist_id):
        return False
    return can_delete_item(user, source) and not is_hidden_from(user, target)


def delegate_permission(user, proxy, action):
    """action is 'add', 'edit' or 'remove'. Creator and admins can do everything."""
    if user is None:
        return False
    if user.is_admin or user.id == proxy.created_by_id:
        return True
    record = proxy.delegate_record(user)
    return bool(record and getattr(record, f"can_{action}_items"))
