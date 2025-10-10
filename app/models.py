from app import db, login_manager
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, session
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login - supports impersonation"""
    # Check if admin is impersonating another user
    if "impersonate_user_id" in session:
        return User.query.get(int(session["impersonate_user_id"]))
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User model - Passwordless authentication via magic links and passkeys"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    has_seen_tour = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wishlist_items = db.relationship(
        "WishlistItem", foreign_keys="WishlistItem.user_id", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    purchases = db.relationship("Purchase", backref="purchased_by", lazy="dynamic", cascade="all, delete-orphan")
    # claims is an alias for purchases (view-only for convenience)
    claims = db.relationship(
        "Purchase",
        lazy="dynamic",
        foreign_keys="Purchase.purchased_by_id",
        viewonly=True,
        overlaps="purchases,purchased_by",
    )
    passkeys = db.relationship("Passkey", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def generate_magic_link_token(self):
        """Generate magic link login token"""
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt="magic-link-salt")

    @staticmethod
    def verify_magic_link_token(token, expiration=None):
        """Verify magic link token and return user"""
        if expiration is None:
            expiration = current_app.config["MAGIC_LINK_TOKEN_EXPIRY"]

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt="magic-link-salt", max_age=expiration)
        except Exception:
            return None
        return User.query.filter_by(email=email).first()

    def __repr__(self):
        return f"<User {self.email}>"


class WishlistItem(db.Model):
    """Wishlist item model"""

    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Who added this item (None = owner)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    image_url = db.Column(db.String(500))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchases = db.relationship("Purchase", backref="wishlist_item", lazy="dynamic", cascade="all, delete-orphan")
    added_by = db.relationship("User", foreign_keys=[added_by_id], backref="custom_gifts_added")

    @property
    def total_purchased(self):
        """Calculate total quantity purchased"""
        return sum([p.quantity for p in self.purchases])

    @property
    def is_fully_purchased(self):
        """Check if item is fully purchased"""
        return self.total_purchased >= self.quantity

    @property
    def is_custom_gift(self):
        """Check if this is a custom gift added by someone other than the owner"""
        return self.added_by_id is not None and self.added_by_id != self.user_id

    def __repr__(self):
        return f"<WishlistItem {self.name}>"


class Purchase(db.Model):
    """Gift claim tracking model - tracks items users have claimed to gift to others"""

    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    wishlist_item_id = db.Column(db.Integer, db.ForeignKey("wishlist_items.id"), nullable=False)
    purchased_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    purchased = db.Column(db.Boolean, default=False)  # Has the gift been purchased/ordered?
    received = db.Column(db.Boolean, default=False)  # Has the gift been received (for online orders)?
    wrapped = db.Column(db.Boolean, default=False)  # Has the gift been wrapped?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Purchase item={self.wishlist_item_id} by={self.purchased_by_id} qty={self.quantity}>"


class WishlistChange(db.Model):
    """Track changes to wishlists for daily digest emails"""

    __tablename__ = "wishlist_changes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    change_type = db.Column(db.String(50), nullable=False)  # 'added', 'updated', 'deleted'
    item_name = db.Column(db.String(200), nullable=False)
    item_id = db.Column(db.Integer)  # May be null if item was deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notified = db.Column(db.Boolean, default=False, index=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("wishlist_changes", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<WishlistChange user={self.user_id} type={self.change_type} item={self.item_name}>"


class Passkey(db.Model):
    """WebAuthn/Passkey credentials for passwordless authentication"""

    __tablename__ = "passkeys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    credential_id = db.Column(db.LargeBinary, nullable=False, unique=True, index=True)
    public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    device_name = db.Column(db.String(100))  # Optional friendly name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Passkey user={self.user_id} device={self.device_name}>"
