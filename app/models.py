from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, session
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login - supports impersonation"""
    # Check if admin is impersonating another user
    if 'impersonate_user_id' in session:
        return User.query.get(int(session['impersonate_user_id']))
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    purchases = db.relationship('Purchase', backref='purchased_by', lazy='dynamic',
                               cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        """Generate password reset token"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(self.email, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expiration=None):
        """Verify password reset token and return user"""
        if expiration is None:
            expiration = current_app.config['PASSWORD_RESET_TOKEN_EXPIRY']

        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(
                token,
                salt='password-reset-salt',
                max_age=expiration
            )
        except Exception:
            return None
        return User.query.filter_by(email=email).first()

    def generate_magic_link_token(self):
        """Generate magic link login token"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(self.email, salt='magic-link-salt')

    @staticmethod
    def verify_magic_link_token(token, expiration=None):
        """Verify magic link token and return user"""
        if expiration is None:
            expiration = current_app.config['MAGIC_LINK_TOKEN_EXPIRY']

        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(
                token,
                salt='magic-link-salt',
                max_age=expiration
            )
        except Exception:
            return None
        return User.query.filter_by(email=email).first()

    def __repr__(self):
        return f'<User {self.email}>'


class WishlistItem(db.Model):
    """Wishlist item model"""
    __tablename__ = 'wishlist_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    image_url = db.Column(db.String(500))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchases = db.relationship('Purchase', backref='wishlist_item', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def total_purchased(self):
        """Calculate total quantity purchased"""
        return sum([p.quantity for p in self.purchases])

    @property
    def is_fully_purchased(self):
        """Check if item is fully purchased"""
        return self.total_purchased >= self.quantity

    def __repr__(self):
        return f'<WishlistItem {self.name}>'


class Purchase(db.Model):
    """Purchase tracking model"""
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    wishlist_item_id = db.Column(db.Integer, db.ForeignKey('wishlist_items.id'), nullable=False)
    purchased_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Purchase item={self.wishlist_item_id} by={self.purchased_by_id} qty={self.quantity}>'
