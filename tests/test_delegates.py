"""Tests for delegate system"""
from app import db
from app.models import User, ProxyWishlist, WishlistDelegate, WishlistItem, Purchase


class TestDelegateAdminRoutes:
    """Test delegate admin management routes"""

    def test_manage_delegates_page_requires_admin(self, client, app, user):
        """Non-admin cannot access delegate management"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=user.id)
            db.session.add(proxy)
            db.session.commit()
            proxy_id = proxy.id

        # Login as non-admin
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        response = client.get(f"/admin/proxy-wishlist/{proxy_id}/delegates", follow_redirects=False)
        assert response.status_code == 302  # Redirects to home or login

        # Or check with follow_redirects
        response = client.get(f"/admin/proxy-wishlist/{proxy_id}/delegates", follow_redirects=True)
        assert response.status_code == 200
        # Just verify they can't access the page (redirected to home)
        assert b"Manage Delegates" not in response.data

    def test_manage_delegates_page_loads(self, client, app, admin_user, user):
        """Admin can view delegate management page"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.commit()
            proxy_id = proxy.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        response = client.get(f"/admin/proxy-wishlist/{proxy_id}/delegates")
        assert response.status_code == 200
        assert b"Delegates" in response.data or b"delegate" in response.data.lower()

    def test_add_delegate(self, client, app, admin_user, user):
        """Admin can add a delegate to proxy wishlist"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.commit()
            proxy_id = proxy.id
            user_id = user.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Add delegate
        response = client.post(
            f"/admin/proxy-wishlist/{proxy_id}/delegates/add", data={"user_id": user_id}, follow_redirects=True
        )
        assert response.status_code == 200

        # Verify delegate was added
        with app.app_context():
            delegate = WishlistDelegate.query.filter_by(proxy_wishlist_id=proxy_id, user_id=user_id).first()
            assert delegate is not None
            assert delegate.can_add_items is True
            assert delegate.can_edit_items is True
            assert delegate.can_remove_items is True

    def test_add_delegate_duplicate(self, client, app, admin_user, user):
        """Cannot add same delegate twice"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.flush()

            # Add delegate first time
            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            proxy_id = proxy.id
            user_id = user.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Try to add delegate again
        response = client.post(
            f"/admin/proxy-wishlist/{proxy_id}/delegates/add", data={"user_id": user_id}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"already a delegate" in response.data

    def test_add_delegate_no_user_id(self, client, app, admin_user):
        """Adding delegate without user_id shows error"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.commit()
            proxy_id = proxy.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Try to add delegate without user_id
        response = client.post(f"/admin/proxy-wishlist/{proxy_id}/delegates/add", data={}, follow_redirects=True)
        assert response.status_code == 200
        assert b"select a user" in response.data.lower()

    def test_remove_delegate(self, client, app, admin_user, user):
        """Admin can remove a delegate"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            delegate_id = delegate.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Remove delegate
        response = client.post(f"/admin/delegate/{delegate_id}/remove", follow_redirects=True)
        assert response.status_code == 200

        # Verify delegate was removed
        with app.app_context():
            deleted_delegate = db.session.get(WishlistDelegate, delegate_id)
            assert deleted_delegate is None

    def test_update_delegate_permissions(self, client, app, admin_user, user):
        """Admin can update delegate permissions"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            delegate_id = delegate.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Update permissions (only can_add_items checked)
        response = client.post(
            f"/admin/delegate/{delegate_id}/update-permissions", data={"can_add_items": "on"}, follow_redirects=True
        )
        assert response.status_code == 200

        # Verify permissions updated
        with app.app_context():
            updated_delegate = db.session.get(WishlistDelegate, delegate_id)
            assert updated_delegate.can_add_items is True
            assert updated_delegate.can_edit_items is False  # Unchecked
            assert updated_delegate.can_remove_items is False  # Unchecked

    def test_update_all_delegate_permissions_off(self, client, app, admin_user, user):
        """Admin can turn off all permissions"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=admin_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            delegate_id = delegate.id

        # Login as admin
        with app.app_context():
            token = admin_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Update permissions (all unchecked)
        response = client.post(f"/admin/delegate/{delegate_id}/update-permissions", data={}, follow_redirects=True)
        assert response.status_code == 200

        # Verify all permissions turned off
        with app.app_context():
            updated_delegate = db.session.get(WishlistDelegate, delegate_id)
            assert updated_delegate.can_add_items is False
            assert updated_delegate.can_edit_items is False
            assert updated_delegate.can_remove_items is False


class TestDelegateWishlistRoutes:
    """Test delegate wishlist management routes"""

    def test_delegate_can_view_manage_page(self, client, app, user, other_user):
        """Delegate can view management page"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            proxy_id = proxy.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        response = client.get(f"/wishlist/manage-delegate/{proxy_id}")
        assert response.status_code == 200
        assert b"Test Child" in response.data

    def test_non_delegate_cannot_view_manage_page(self, client, app, user, other_user):
        """Non-delegate cannot view management page"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.commit()
            proxy_id = proxy.id

        # Login as non-delegate user
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        response = client.get(f"/wishlist/manage-delegate/{proxy_id}", follow_redirects=False)
        # Should redirect (302) or return error
        assert response.status_code in [302, 403, 404]

        # With follow_redirects, verify they're denied
        response = client.get(f"/wishlist/manage-delegate/{proxy_id}", follow_redirects=True)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert b"permission" in response.data.lower() or b"not authorized" in response.data.lower()

    def test_delegate_can_add_item(self, client, app, user, other_user):
        """Delegate can add item to proxy wishlist"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.commit()
            proxy_id = proxy.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Add item
        response = client.post(
            f"/wishlist/delegate/add-item/{proxy_id}",
            data={
                "name": "Delegate Added Item",
                "description": "Test description",
                "price": "25.99",
                "quantity": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Verify item was added
        with app.app_context():
            item = WishlistItem.query.filter_by(proxy_wishlist_id=proxy_id, name="Delegate Added Item").first()
            assert item is not None
            assert item.added_by_id == user.id
            # Items added by delegates are NOT custom gifts
            assert item.is_custom_gift is False

    def test_delegate_can_edit_item(self, client, app, user, other_user):
        """Delegate can edit items on proxy wishlist"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.flush()

            item = WishlistItem(
                proxy_wishlist_id=proxy.id,
                added_by_id=user.id,
                name="Original Name",
                description="Original description",
                price=10.0,
                quantity=1,
            )
            db.session.add(item)
            db.session.commit()
            proxy_id = proxy.id
            item_id = item.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Edit item
        response = client.post(
            f"/wishlist/delegate/edit-item/{item_id}",
            data={"name": "Updated Name", "description": "Updated description", "price": "15.99", "quantity": "2"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Verify item was updated
        with app.app_context():
            updated_item = db.session.get(WishlistItem, item_id)
            assert updated_item.name == "Updated Name"
            assert updated_item.description == "Updated description"
            assert updated_item.price == 15.99
            assert updated_item.quantity == 2

    def test_delegate_can_delete_item(self, client, app, user, other_user):
        """Delegate can delete items from proxy wishlist"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.flush()

            item = WishlistItem(
                proxy_wishlist_id=proxy.id,
                added_by_id=user.id,
                name="To Delete",
                description="Will be deleted",
                price=10.0,
                quantity=1,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Delete item
        response = client.post(f"/wishlist/delete/{item_id}", follow_redirects=True)
        assert response.status_code == 200

        # Verify item was deleted
        with app.app_context():
            deleted_item = db.session.get(WishlistItem, item_id)
            assert deleted_item is None

    def test_delegate_cannot_see_other_custom_gifts(self, client, app, user, other_user):
        """Delegate cannot see custom gifts added by others"""
        with app.app_context():
            third_user = User(name="Third User", email="third@test.com")
            db.session.add(third_user)
            db.session.flush()

            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.flush()

            # Delegate's item (should be visible)
            item1 = WishlistItem(
                proxy_wishlist_id=proxy.id,
                added_by_id=user.id,
                name="Delegate Item",
                description="Added by delegate",
                price=10.0,
                quantity=1,
            )
            db.session.add(item1)

            # Other user's custom gift (should NOT be visible)
            item2 = WishlistItem(
                proxy_wishlist_id=proxy.id,
                added_by_id=third_user.id,
                name="Other Custom Gift",
                description="Added by another user",
                price=20.0,
                quantity=1,
            )
            db.session.add(item2)
            db.session.commit()
            proxy_id = proxy.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # View proxy wishlist
        response = client.get(f"/wishlist/view-proxy/{proxy_id}")
        assert response.status_code == 200
        assert b"Delegate Item" in response.data
        assert b"Other Custom Gift" not in response.data  # Should not see other user's custom gift

    def test_delegate_can_see_own_custom_gift(self, client, app, user, other_user):
        """Delegate can see their own custom gifts"""
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=other_user.id)
            db.session.add(proxy)
            db.session.flush()

            delegate = WishlistDelegate(
                proxy_wishlist_id=proxy.id,
                user_id=user.id,
                can_add_items=True,
                can_edit_items=True,
                can_remove_items=True,
            )
            db.session.add(delegate)
            db.session.flush()

            # Own item
            item = WishlistItem(
                proxy_wishlist_id=proxy.id,
                added_by_id=user.id,
                name="My Item",
                description="My own item",
                price=10.0,
                quantity=1,
            )
            db.session.add(item)
            db.session.commit()
            proxy_id = proxy.id

        # Login as delegate
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # View manage page
        response = client.get(f"/wishlist/manage-delegate/{proxy_id}")
        assert response.status_code == 200
        assert b"My Item" in response.data

    def test_non_delegate_can_see_all_custom_gifts(self, client, app, user, other_user):
        """Non-delegate can see all custom gifts on proxy wishlist"""
        # Create proxy wishlist
        with app.app_context():
            proxy = ProxyWishlist(name="Test Child", email="child@test.com", created_by_id=user.id)
            db.session.add(proxy)
            db.session.flush()
            proxy_id = proxy.id

            # user is a delegate
            delegate = WishlistDelegate(proxy_wishlist_id=proxy_id, user_id=user.id, can_add_items=True)
            db.session.add(delegate)
            db.session.flush()

            # Add delegate's item (should show as regular item, not custom gift)
            delegate_item = WishlistItem(
                proxy_wishlist_id=proxy_id, name="Delegate Item", quantity=1, added_by_id=user.id
            )
            db.session.add(delegate_item)

            # Add custom gift from another user
            custom_gift = WishlistItem(
                proxy_wishlist_id=proxy_id, name="Custom Gift", quantity=1, added_by_id=other_user.id
            )
            db.session.add(custom_gift)
            db.session.commit()

        # Login as a third user who is NOT a delegate
        with app.app_context():
            third_user = User(email="third@test.com", name="Third User", is_admin=False)
            db.session.add(third_user)
            db.session.commit()
            token = third_user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # View proxy wishlist as non-delegate
        response = client.get(f"/wishlist/view-proxy/{proxy_id}")
        assert response.status_code == 200
        assert b"Delegate Item" in response.data  # Can see delegate's item
        assert b"Custom Gift" in response.data  # CAN see other user's custom gift (non-delegate privilege)
