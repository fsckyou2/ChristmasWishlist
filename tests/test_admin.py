import pytest
from app.models import User, WishlistItem
from app import db


class TestAdminRoutes:
    """Test admin routes"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

    def test_admin_dashboard_requires_admin(self, client, app, user):
        """Test admin dashboard requires admin privileges"""
        self.login_user(client, app, user)
        response = client.get("/admin/dashboard", follow_redirects=True)
        assert b"administrator" in response.data

    def test_admin_dashboard_loads(self, client, app, admin_user):
        """Test admin dashboard loads for admin"""
        self.login_user(client, app, admin_user)
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        assert b"Admin" in response.data or b"Dashboard" in response.data

    def test_admin_users_page(self, client, app, admin_user):
        """Test admin users page"""
        self.login_user(client, app, admin_user)
        response = client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_view_user(self, client, app, admin_user, user):
        """Test admin viewing user details"""
        self.login_user(client, app, admin_user)
        response = client.get(f"/admin/user/{user.id}")
        assert response.status_code == 200
        assert user.name.encode() in response.data

    def test_admin_edit_user(self, client, app, admin_user, user):
        """Test admin editing user"""
        self.login_user(client, app, admin_user)
        response = client.post(
            f"/admin/user/{user.id}/edit",
            data={"name": "Updated Name", "email": user.email},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"updated successfully" in response.data

        # Verify update
        with app.app_context():
            updated_user = User.query.get(user.id)
            assert updated_user.name == "Updated Name"

    def test_admin_toggle_admin_status(self, client, app, admin_user, user):
        """Test admin toggling admin status"""
        self.login_user(client, app, admin_user)

        assert user.is_admin is False

        response = client.post(f"/admin/user/{user.id}/toggle-admin", follow_redirects=True)
        assert response.status_code == 200

        # Verify status changed
        with app.app_context():
            updated_user = User.query.get(user.id)
            assert updated_user.is_admin is True

    def test_admin_cannot_toggle_own_status(self, client, app, admin_user):
        """Test admin cannot change their own admin status"""
        self.login_user(client, app, admin_user)
        response = client.post(f"/admin/user/{admin_user.id}/toggle-admin", follow_redirects=True)
        assert b"cannot change your own" in response.data

    def test_admin_delete_user(self, client, app, admin_user, user):
        """Test admin deleting user"""
        self.login_user(client, app, admin_user)
        user_id = user.id

        response = client.post(f"/admin/user/{user_id}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"deleted" in response.data

        # Verify deletion
        with app.app_context():
            deleted_user = User.query.get(user_id)
            assert deleted_user is None

    def test_admin_cannot_delete_self(self, client, app, admin_user):
        """Test admin cannot delete themselves"""
        self.login_user(client, app, admin_user)
        response = client.post(f"/admin/user/{admin_user.id}/delete", follow_redirects=True)
        assert b"cannot delete your own" in response.data

    def test_admin_send_login_link(self, client, app, admin_user, user):
        """Test admin sending login link to user"""
        self.login_user(client, app, admin_user)
        response = client.post(f"/admin/user/{user.id}/send-login-link", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login link sent" in response.data

    def test_admin_impersonate_user(self, client, app, admin_user, user):
        """Test admin impersonating user"""
        self.login_user(client, app, admin_user)
        response = client.get(f"/admin/user/{user.id}/impersonate", follow_redirects=True)
        assert response.status_code == 200
        assert b"impersonating" in response.data.lower()

    def test_admin_cannot_impersonate_self(self, client, app, admin_user):
        """Test admin cannot impersonate themselves"""
        self.login_user(client, app, admin_user)
        response = client.get(f"/admin/user/{admin_user.id}/impersonate", follow_redirects=True)
        assert b"cannot impersonate yourself" in response.data

    def test_admin_stop_impersonate(self, client, app, admin_user, user):
        """Test stopping impersonation"""
        self.login_user(client, app, admin_user)

        # Start impersonating
        client.get(f"/admin/user/{user.id}/impersonate")

        # Stop impersonating
        response = client.get("/admin/stop-impersonate", follow_redirects=True)
        assert response.status_code == 200
        assert b"Stopped impersonating" in response.data

    def test_admin_items_page(self, client, app, admin_user):
        """Test admin items page"""
        self.login_user(client, app, admin_user)
        response = client.get("/admin/items")
        assert response.status_code == 200

    def test_admin_delete_item(self, client, app, admin_user, wishlist_item):
        """Test admin deleting item"""
        self.login_user(client, app, admin_user)
        item_id = wishlist_item.id

        response = client.post(f"/admin/item/{item_id}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"deleted" in response.data

        # Verify deletion
        with app.app_context():
            deleted_item = WishlistItem.query.get(item_id)
            assert deleted_item is None

    def test_admin_purchases_page(self, client, app, admin_user):
        """Test admin purchases page"""
        self.login_user(client, app, admin_user)
        response = client.get("/admin/purchases")
        assert response.status_code == 200

    def test_admin_can_edit_any_item_from_admin_area(self, client, app, admin_user, user):
        """Test admin can edit any user's item from admin area"""
        self.login_user(client, app, admin_user)

        # Create item owned by regular user
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="User's Item", quantity=1)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Admin edits item from admin area
        response = client.post(
            f"/admin/item/{item_id}/edit",
            data={
                "name": "Admin Edited Item",
                "url": "https://example.com",
                "description": "Edited by admin",
                "price": 99.99,
                "quantity": 2,
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"updated" in response.data

        # Verify update
        with app.app_context():
            updated_item = WishlistItem.query.get(item_id)
            assert updated_item.name == "Admin Edited Item"
            assert updated_item.description == "Edited by admin"
            assert updated_item.price == 99.99

    def test_admin_can_edit_any_item_via_wishlist_route(self, client, app, admin_user, user):
        """Test admin can edit any user's item via wishlist edit route"""
        self.login_user(client, app, admin_user)

        # Create item owned by regular user
        with app.app_context():
            item = WishlistItem(user_id=user.id, name="User's Item", quantity=1)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Admin edits item via wishlist route
        response = client.post(
            f"/wishlist/edit/{item_id}",
            data={
                "name": "Admin Edited via Wishlist",
                "url": "https://example.com",
                "description": "Edited by admin via wishlist",
                "price": 55.55,
                "quantity": 3,
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify update
        with app.app_context():
            updated_item = WishlistItem.query.get(item_id)
            assert updated_item.name == "Admin Edited via Wishlist"
            assert updated_item.description == "Edited by admin via wishlist"

    def test_non_admin_cannot_edit_others_items(self, client, app, user, other_user):
        """Test non-admin cannot edit other users' items"""
        self.login_user(client, app, user)

        # Create item owned by other user
        with app.app_context():
            item = WishlistItem(user_id=other_user.id, name="Other User's Item", quantity=1)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # User tries to edit other user's item
        response = client.post(
            f"/wishlist/edit/{item_id}",
            data={"name": "Hacked Item", "quantity": 1},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"You can only edit items you added" in response.data

        # Verify item was not changed
        with app.app_context():
            item = WishlistItem.query.get(item_id)
            assert item.name == "Other User's Item"
