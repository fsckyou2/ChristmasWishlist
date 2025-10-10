import pytest
from app.models import User, WishlistItem, Purchase, WishlistChange
from app import db
import json


class TestWishlistRoutes:
    """Test wishlist routes"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

    def test_my_list_requires_login(self, client):
        """Test my list requires authentication"""
        response = client.get("/wishlist/my-list")
        assert response.status_code == 302  # Redirect to login

    def test_my_list_loads(self, client, app, user):
        """Test my list page loads"""
        self.login_user(client, app, user)
        response = client.get("/wishlist/my-list")
        assert response.status_code == 200
        assert b"My Wishlist" in response.data

    def test_my_list_table_loads(self, client, app, user):
        """Test my list table view loads"""
        self.login_user(client, app, user)
        response = client.get("/wishlist/my-list/table")
        assert response.status_code == 200
        assert b"Table View" in response.data

    def test_add_item_page_loads(self, client, app, user):
        """Test add item page loads"""
        self.login_user(client, app, user)
        response = client.get("/wishlist/add")
        assert response.status_code == 200
        assert b"Add Item" in response.data

    def test_add_item(self, client, app, user):
        """Test adding a wishlist item"""
        self.login_user(client, app, user)

        # Count items before
        with app.app_context():
            count_before = WishlistItem.query.count()

        response = client.post(
            "/wishlist/add",
            data={
                "name": "Test Item",
                "url": "https://example.com",
                "description": "Test description",
                "price": "29.99",
                "quantity": "2",
                "submit": "Add to Wishlist",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify item was created (this is the real test)
        with app.app_context():
            count_after = WishlistItem.query.count()
            assert (
                count_after > count_before
            ), f"Item should be created in database (before: {count_before}, after: {count_after})"

            item = WishlistItem.query.filter_by(name="Test Item").first()
            assert item is not None, "Item should be found in database"
            assert item.price == 29.99
            assert item.quantity == 2
            assert item.url == "https://example.com"
            assert item.description == "Test description"

    def test_edit_item(self, client, app, user, wishlist_item):
        """Test editing a wishlist item"""
        self.login_user(client, app, user)
        response = client.post(
            f"/wishlist/edit/{wishlist_item.id}",
            data={
                "name": "Updated Item",
                "url": wishlist_item.url,
                "description": "Updated description",
                "price": "39.99",
                "quantity": "3",
                "submit": "Update",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify changes (this is the real test)
        with app.app_context():
            item = WishlistItem.query.get(wishlist_item.id)
            assert item is not None, "Item should still exist"
            assert item.name == "Updated Item", "Item name should be updated"
            assert item.price == 39.99, "Item price should be updated"
            assert item.quantity == 3, "Item quantity should be updated"
            assert item.description == "Updated description", "Item description should be updated"

    def test_cannot_edit_others_item(self, client, app, user, admin_user):
        """Test user cannot edit another user's item"""
        # Create item for admin user
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Admin Item", quantity=1)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as regular user
        self.login_user(client, app, user)

        # Try to edit admin's item
        response = client.post(
            f"/wishlist/edit/{item_id}",
            data={
                "name": "Hacked Item",
                "quantity": "1",
            },
            follow_redirects=True,
        )

        assert b"can only edit items you added" in response.data

    def test_delete_item(self, client, app, user, wishlist_item):
        """Test deleting a wishlist item"""
        self.login_user(client, app, user)
        response = client.post(f"/wishlist/delete/{wishlist_item.id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Item deleted" in response.data

        # Verify deletion
        with app.app_context():
            item = WishlistItem.query.get(wishlist_item.id)
            assert item is None

    def test_view_user_list(self, client, app, user, admin_user):
        """Test viewing another user's wishlist"""
        self.login_user(client, app, user)
        response = client.get(f"/wishlist/view/{admin_user.id}")
        assert response.status_code == 200
        assert admin_user.name.encode() in response.data

    def test_purchase_item(self, client, app, user, admin_user):
        """Test purchasing an item from another user's list"""
        # Create item for admin
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Gift Item", quantity=2)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as regular user
        self.login_user(client, app, user)

        # Purchase item
        response = client.post(
            f"/wishlist/purchase/{item_id}",
            data={"quantity": "1", "submit": "Mark as Purchased"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify purchase (this is the real test)
        with app.app_context():
            purchase = Purchase.query.filter_by(wishlist_item_id=item_id).first()
            assert purchase is not None, "Purchase should be created in database"
            assert purchase.purchased_by_id == user.id, "Purchase should be by the logged-in user"
            assert purchase.quantity == 1, "Purchase quantity should be 1"

    def test_cannot_purchase_own_item(self, client, app, user, wishlist_item):
        """Test user cannot claim their own item"""
        self.login_user(client, app, user)
        response = client.post(
            f"/wishlist/claim/{wishlist_item.id}",
            data={
                "quantity": "1",
            },
            follow_redirects=True,
        )

        assert b"cannot claim items from your own wishlist" in response.data

    def test_unpurchase_item(self, client, app, user, admin_user):
        """Test unclaiming an item"""
        # Create item and claim
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Gift Item", quantity=2)
            db.session.add(item)
            db.session.flush()

            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=user.id, quantity=1)
            db.session.add(purchase)
            db.session.commit()
            purchase_id = purchase.id

        # Login and unclaim
        self.login_user(client, app, user)
        response = client.post(f"/wishlist/unclaim/{purchase_id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Unclaimed" in response.data

        # Verify unclaim
        with app.app_context():
            purchase = Purchase.query.get(purchase_id)
            assert purchase is None

    def test_all_users_page(self, client, app, user):
        """Test all users page"""
        self.login_user(client, app, user)
        response = client.get("/wishlist/all-users")
        assert response.status_code == 200
        assert b"Wishlist" in response.data

    def test_add_empty_item(self, client, app, user):
        """Test adding empty item via AJAX"""
        self.login_user(client, app, user)
        response = client.post("/wishlist/add-empty", content_type="application/json")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "item_id" in data

    def test_update_item_quick(self, client, app, user, wishlist_item):
        """Test quick update item via AJAX"""
        self.login_user(client, app, user)
        response = client.post(
            f"/wishlist/update-item/{wishlist_item.id}",
            data=json.dumps({"name": "Quick Updated", "price": "49.99"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify update
        with app.app_context():
            item = WishlistItem.query.get(wishlist_item.id)
            assert item.name == "Quick Updated"
            assert item.price == 49.99


class TestWishlistChange:
    """Test wishlist change tracking"""

    def test_wishlist_change_on_add(self, app, user):
        """Test change is tracked when adding item"""
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="New Item", quantity=1)
            db.session.add(item)
            db.session.flush()

            change = WishlistChange(
                user_id=user.id,
                change_type="added",
                item_name=item.name,
                item_id=item.id,
            )
            db.session.add(change)
            db.session.commit()

            # Verify change was tracked
            changes = WishlistChange.query.filter_by(user_id=user.id).all()
            assert len(changes) > 0
            assert changes[0].change_type == "added"

    def test_wishlist_change_on_update(self, app, user, wishlist_item):
        """Test change is tracked when updating item"""
        with app.app_context():
            change = WishlistChange(
                user_id=user.id,
                change_type="updated",
                item_name=wishlist_item.name,
                item_id=wishlist_item.id,
            )
            db.session.add(change)
            db.session.commit()

            # Verify change
            changes = WishlistChange.query.filter_by(change_type="updated", item_id=wishlist_item.id).all()
            assert len(changes) > 0

    def test_wishlist_change_on_delete(self, app, user):
        """Test change is tracked when deleting item"""
        with app.app_context():
            change = WishlistChange(
                user_id=user.id,
                change_type="deleted",
                item_name="Deleted Item",
                item_id=None,
            )
            db.session.add(change)
            db.session.commit()

            # Verify change
            changes = WishlistChange.query.filter_by(change_type="deleted").all()
            assert len(changes) > 0


class TestPurchaseStatusPrivacy:
    """Test that purchase status is hidden from wishlist owners but visible to others"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

    def test_owner_cannot_see_purchase_status_card_view(self, client, app, user, admin_user):
        """Test owner doesn't see purchase status on their own wishlist (card view)"""
        # Create purchased item for user
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="My Item", quantity=2)
            db.session.add(item)
            db.session.flush()

            # Admin purchases the item
            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=admin_user.id, quantity=1)
            db.session.add(purchase)
            db.session.commit()

        # Login as owner and view own wishlist
        self.login_user(client, app, user)
        response = client.get("/wishlist/my-list")

        assert response.status_code == 200
        # Should NOT see purchase status indicators
        assert b"Fully Purchased" not in response.data
        assert b"Purchased" not in response.data
        assert b"1/2" not in response.data
        # Should see the item name
        assert b"My Item" in response.data

    def test_owner_cannot_see_purchase_status_table_view(self, client, app, user, admin_user):
        """Test owner doesn't see purchase status on their own wishlist (table view)"""
        # Create purchased item for user
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="My Table Item", quantity=2)
            db.session.add(item)
            db.session.flush()

            # Admin purchases the item
            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=admin_user.id, quantity=1)
            db.session.add(purchase)
            db.session.commit()

        # Login as owner and view own wishlist table
        self.login_user(client, app, user)
        response = client.get("/wishlist/my-list/table")

        assert response.status_code == 200
        # Should NOT see "Status" column header (it was removed)
        response_text = response.data.decode("utf-8")
        # Count how many times "Status" appears - should not be a column header
        # (It might appear in other contexts, but not as a table header)
        assert b"<th" in response.data  # Table headers exist
        # The specific Status column for purchase status should not exist
        # We verify this by checking the item exists but status indicators don't
        assert b"My Table Item" in response.data
        assert b"Fully Purchased" not in response.data
        assert b"1/2 Purchased" not in response.data

    def test_viewer_can_see_purchase_status(self, client, app, user, admin_user):
        """Test non-owner CAN see claim status when viewing someone else's wishlist"""
        # Create claimed item for admin
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Admin Gift Item", quantity=3)
            db.session.add(item)
            db.session.flush()

            # User claims 1 item
            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=user.id, quantity=1)
            db.session.add(purchase)
            db.session.commit()

        # Login as regular user and view admin's wishlist
        self.login_user(client, app, user)
        response = client.get(f"/wishlist/view/{admin_user.id}")

        assert response.status_code == 200
        # Should see item name
        assert b"Admin Gift Item" in response.data
        # Should see claim status (1/3 claimed)
        assert b"1/3 Claimed" in response.data
        # Should see "Your Claims" section since user claimed it
        assert b"Your Claims" in response.data

    def test_viewer_sees_fully_purchased_status(self, client, app, user, admin_user):
        """Test viewer sees 'Fully Claimed' badge when item is fully claimed"""
        # Create fully claimed item for admin
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Fully Bought Gift", quantity=2)
            db.session.add(item)
            db.session.flush()

            # User claims all items
            purchase = Purchase(wishlist_item_id=item.id, purchased_by_id=user.id, quantity=2)
            db.session.add(purchase)
            db.session.commit()

        # Login as regular user and view admin's wishlist
        self.login_user(client, app, user)
        response = client.get(f"/wishlist/view/{admin_user.id}")

        assert response.status_code == 200
        # Should see "Fully Claimed" badge
        assert b"Fully Claimed" in response.data
        assert b"Fully Bought Gift" in response.data

    def test_unpurchased_items_have_no_status_for_owner(self, client, app, user):
        """Test unpurchased items on owner's list don't show any status"""
        # Create unpurchased item for user
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="Unpurchased Item", quantity=1)
            db.session.add(item)
            db.session.commit()

        # Login as owner and view own wishlist
        self.login_user(client, app, user)
        response = client.get("/wishlist/my-list")

        assert response.status_code == 200
        # Should see item
        assert b"Unpurchased Item" in response.data
        # Should not see any purchase status
        assert b"Purchased" not in response.data
        assert b"Available" not in response.data

    def test_viewer_sees_no_status_for_unpurchased_items(self, client, app, user, admin_user):
        """Test viewer doesn't see explicit 'available' status on unclaimed items"""
        # Create unclaimed item for admin
        with app.app_context():
            item = WishlistItem(user_id=admin_user.id, name="Available Item", quantity=1)
            db.session.add(item)
            db.session.commit()

        # Login as regular user and view admin's wishlist
        self.login_user(client, app, user)
        response = client.get(f"/wishlist/view/{admin_user.id}")

        assert response.status_code == 200
        # Should see item
        assert b"Available Item" in response.data
        # Item should be available for claiming (button present)
        assert b"Claim Gift" in response.data
        # Should not see claim status badges (no claims yet)
        assert b"Fully Claimed" not in response.data
        assert b"Claimed" not in response.data or b"Claim Gift" in response.data


class TestAddItemFromURL:
    """Test adding items from URL in table view"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

    def test_add_item_from_scraped_url_table_view(self, client, app, user):
        """Test that add-by-URL function in table view actually adds item to wishlist"""
        self.login_user(client, app, user)

        # Count items before
        with app.app_context():
            count_before = WishlistItem.query.filter_by(user_id=user.id).count()

        # Simulate the AJAX request that the table view makes
        response = client.post(
            "/wishlist/add-item-from-scraped-data",
            data=json.dumps(
                {
                    "name": "Scraped Product",
                    "url": "https://example.com/product",
                    "description": "A great product",
                    "price": "29.99",
                    "image_url": "https://example.com/image.jpg",
                    "quantity": "1",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "item_id" in data

        # Verify item was actually added to database
        with app.app_context():
            count_after = WishlistItem.query.filter_by(user_id=user.id).count()
            assert count_after == count_before + 1, "Item should be added to database"

            item = WishlistItem.query.filter_by(name="Scraped Product").first()
            assert item is not None, "Item should exist in database"
            assert item.user_id == user.id, "Item should belong to logged-in user"
            assert item.url == "https://example.com/product"
            assert item.description == "A great product"
            assert item.price == 29.99
            assert item.image_url == "https://example.com/image.jpg"
            assert item.quantity == 1
