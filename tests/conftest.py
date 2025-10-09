import pytest
from app import create_app, db
from app.models import User, WishlistItem, Purchase


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def user(app):
    """Create a test user"""
    user = User(
        email='test@example.com',
        name='Test User',
        is_admin=False
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    """Create an admin user"""
    admin = User(
        email='admin@example.com',
        name='Admin User',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def wishlist_item(app, user):
    """Create a test wishlist item"""
    item = WishlistItem(
        user_id=user.id,
        name='Test Product',
        url='https://example.com/product',
        description='A test product',
        price=29.99,
        image_url='https://example.com/image.jpg',
        quantity=2
    )
    db.session.add(item)
    db.session.commit()
    return item
