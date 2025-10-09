import pytest
from app.models import User, WishlistItem, Purchase
from app import db


class TestUserModel:
    """Test User model"""

    def test_create_user(self, app):
        """Test creating a user"""
        user = User(email='newuser@example.com', name='New User')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.email == 'newuser@example.com'
        assert user.name == 'New User'
        assert user.is_admin is False
        assert user.check_password('password123') is True
        assert user.check_password('wrongpassword') is False

    def test_user_password_hashing(self, app):
        """Test that passwords are properly hashed"""
        user = User(email='test@example.com', name='Test')
        user.set_password('mypassword')

        assert user.password_hash != 'mypassword'
        assert user.check_password('mypassword')
        assert not user.check_password('wrongpassword')

    def test_generate_reset_token(self, app, user):
        """Test generating password reset token"""
        token = user.generate_reset_token()
        assert token is not None
        assert isinstance(token, str)

    def test_verify_reset_token(self, app, user):
        """Test verifying password reset token"""
        token = user.generate_reset_token()
        verified_user = User.verify_reset_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id

    def test_verify_invalid_token(self, app):
        """Test verifying invalid token"""
        verified_user = User.verify_reset_token('invalid-token')
        assert verified_user is None

    def test_generate_magic_link_token(self, app, user):
        """Test generating magic link token"""
        token = user.generate_magic_link_token()
        assert token is not None
        assert isinstance(token, str)

    def test_verify_magic_link_token(self, app, user):
        """Test verifying magic link token"""
        token = user.generate_magic_link_token()
        verified_user = User.verify_magic_link_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id


class TestWishlistItemModel:
    """Test WishlistItem model"""

    def test_create_wishlist_item(self, app, user):
        """Test creating a wishlist item"""
        item = WishlistItem(
            user_id=user.id,
            name='Product Name',
            url='https://example.com/product',
            description='Product description',
            price=19.99,
            image_url='https://example.com/image.jpg',
            quantity=1
        )
        db.session.add(item)
        db.session.commit()

        assert item.id is not None
        assert item.user_id == user.id
        assert item.name == 'Product Name'
        assert item.price == 19.99
        assert item.quantity == 1

    def test_wishlist_item_relationship(self, app, user):
        """Test relationship between User and WishlistItem"""
        item1 = WishlistItem(user_id=user.id, name='Item 1', quantity=1)
        item2 = WishlistItem(user_id=user.id, name='Item 2', quantity=2)
        db.session.add_all([item1, item2])
        db.session.commit()

        assert len(user.wishlist_items) == 2
        assert item1 in user.wishlist_items
        assert item2 in user.wishlist_items

    def test_total_purchased_property(self, app, user, wishlist_item):
        """Test total_purchased property"""
        assert wishlist_item.total_purchased == 0

        purchase = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=user.id,
            quantity=1
        )
        db.session.add(purchase)
        db.session.commit()

        assert wishlist_item.total_purchased == 1

    def test_is_fully_purchased_property(self, app, user, wishlist_item):
        """Test is_fully_purchased property"""
        wishlist_item.quantity = 2
        db.session.commit()

        assert wishlist_item.is_fully_purchased is False

        purchase = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=user.id,
            quantity=2
        )
        db.session.add(purchase)
        db.session.commit()

        assert wishlist_item.is_fully_purchased is True


class TestPurchaseModel:
    """Test Purchase model"""

    def test_create_purchase(self, app, user, wishlist_item):
        """Test creating a purchase"""
        purchase = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=user.id,
            quantity=1
        )
        db.session.add(purchase)
        db.session.commit()

        assert purchase.id is not None
        assert purchase.wishlist_item_id == wishlist_item.id
        assert purchase.purchased_by_id == user.id
        assert purchase.quantity == 1

    def test_purchase_relationships(self, app, user, wishlist_item):
        """Test relationships in Purchase model"""
        purchase = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=user.id,
            quantity=1
        )
        db.session.add(purchase)
        db.session.commit()

        assert purchase.wishlist_item == wishlist_item
        assert purchase.purchased_by == user
        assert purchase in wishlist_item.purchases

    def test_multiple_purchases(self, app, user, admin_user, wishlist_item):
        """Test multiple users purchasing same item"""
        wishlist_item.quantity = 5
        db.session.commit()

        purchase1 = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=user.id,
            quantity=2
        )
        purchase2 = Purchase(
            wishlist_item_id=wishlist_item.id,
            purchased_by_id=admin_user.id,
            quantity=3
        )
        db.session.add_all([purchase1, purchase2])
        db.session.commit()

        assert len(wishlist_item.purchases) == 2
        assert wishlist_item.total_purchased == 5
        assert wishlist_item.is_fully_purchased is True
