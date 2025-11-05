#!/usr/bin/env python3
"""
Fix Rebecca's items on Westley's proxy wishlist:
1. Make Rebecca a delegate of Westley's wishlist
2. Delete all Purchase/claim records for Rebecca's items on that wishlist
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from app.models import User, ProxyWishlist, WishlistItem, Purchase, WishlistDelegate  # noqa: E402


def fix_rebecca_westley():
    app = create_app()

    with app.app_context():
        # Find Rebecca
        rebecca = User.query.filter_by(name="Rebecca").first()
        if not rebecca:
            print("ERROR: Rebecca not found")
            return
        print(f"Found Rebecca (ID: {rebecca.id})")

        # Find Westley's proxy wishlist
        westley_proxy = ProxyWishlist.query.filter_by(name="Westley").first()
        if not westley_proxy:
            print("ERROR: Westley's proxy wishlist not found")
            return
        print(f"Found Westley's proxy wishlist (ID: {westley_proxy.id})")

        # Find Rebecca's items on Westley's wishlist
        rebecca_items = WishlistItem.query.filter_by(proxy_wishlist_id=westley_proxy.id, added_by_id=rebecca.id).all()
        print(f"\nFound {len(rebecca_items)} items added by Rebecca:")
        for item in rebecca_items:
            print(f"  - {item.name} (ID: {item.id})")

        # Check if Rebecca is already a delegate
        existing_delegate = WishlistDelegate.query.filter_by(
            proxy_wishlist_id=westley_proxy.id, user_id=rebecca.id
        ).first()

        if existing_delegate:
            print("\nRebecca is already a delegate")
        else:
            # Make Rebecca a delegate with full permissions
            delegate = WishlistDelegate(
                proxy_wishlist_id=westley_proxy.id,
                user_id=rebecca.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            print("\nAdded Rebecca as delegate with full permissions")

        # Find and delete all Purchase records for Rebecca's items
        purchases_to_delete = []
        for item in rebecca_items:
            purchases = Purchase.query.filter_by(wishlist_item_id=item.id).all()
            purchases_to_delete.extend(purchases)

        if purchases_to_delete:
            print(f"\nDeleting {len(purchases_to_delete)} claim records:")
            for purchase in purchases_to_delete:
                item_name = purchase.wishlist_item.name
                claimed_by = purchase.purchased_by.name
                quantity = purchase.quantity
                print(f"  - Item: {item_name}, Claimed by: {claimed_by}, Quantity: {quantity}")
                db.session.delete(purchase)
        else:
            print("\nNo claim records to delete")

        # Commit changes
        db.session.commit()
        print("\n✅ Changes committed successfully!")
        print("\nSummary:")
        print("  - Rebecca is now a delegate of Westley's wishlist")
        print(f"  - {len(purchases_to_delete)} claim records deleted")
        print(f"  - {len(rebecca_items)} items are now regular (non-custom) items")


if __name__ == "__main__":
    fix_rebecca_westley()
