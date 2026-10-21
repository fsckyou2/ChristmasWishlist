import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, session
from flask_login import UserMixin
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


def utcnow():
    """Naive UTC timestamp, matching how existing rows are stored in SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@login_manager.user_loader
def load_user(user_id):
    """Load the logged-in user, or the user an admin is impersonating.

    Impersonation only applies while the real logged-in account is still an admin; while it is active the admin sees
    exactly what the impersonated user sees (including their surprise-protection rules).
    """
    user = db.session.get(User, int(user_id))
    target_id = session.get("impersonate_user_id")
    if target_id is not None:
        target = db.session.get(User, int(target_id)) if user is not None and user.is_admin else None
        if target is not None:
            return target
        session.pop("impersonate_user_id", None)
    return user


class User(UserMixin, db.Model):
    """User model - Supports both passwordless (magic links/passkeys) and username/password authentication"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # Optional for username/password users
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)  # For username/password auth
    password_hash = db.Column(db.String(255), nullable=True)  # For username/password auth
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    has_seen_tour = db.Column(db.Boolean, default=False)
    # Changes on every login; magic-link tokens embed it, which makes each link single-use
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    wishlist_items = db.relationship(
        "WishlistItem",
        foreign_keys="WishlistItem.user_id",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    claims = db.relationship("Claim", back_populates="claimed_by", lazy="dynamic", cascade="all, delete-orphan")
    passkeys = db.relationship("Passkey", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def _magic_link_serializer(self):
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="magic-link-v2")

    def generate_magic_link_token(self):
        """Generate a magic link login token, valid until it expires or the user next logs in."""
        if not self.email:
            return None
        last_login = self.last_login_at.isoformat() if self.last_login_at else None
        return self._magic_link_serializer().dumps({"uid": self.id, "email": self.email, "ll": last_login})

    @staticmethod
    def verify_magic_link_token(token, expiration=None):
        """Return the user for a valid, unused, unexpired magic link token, else None."""
        if expiration is None:
            expiration = current_app.config["MAGIC_LINK_TOKEN_EXPIRY"]
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="magic-link-v2")
        try:
            payload = serializer.loads(token, max_age=expiration)
        except BadSignature:
            return None
        if not isinstance(payload, dict):
            return None
        user = db.session.get(User, payload.get("uid"))
        if user is None or user.email != payload.get("email"):
            return None
        last_login = user.last_login_at.isoformat() if user.last_login_at else None
        if last_login != payload.get("ll"):
            return None  # already used (or superseded by a later login)
        return user

    def record_login(self):
        self.last_login_at = utcnow()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email or self.username}>"


class WishlistItem(db.Model):
    """An item on exactly one list: a user's (user_id) or a proxy wishlist's (proxy_wishlist_id)."""

    __tablename__ = "wishlist_items"
    __table_args__ = (
        db.CheckConstraint(
            "(user_id IS NULL) <> (proxy_wishlist_id IS NULL)", name="ck_wishlist_items_exactly_one_owner"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    proxy_wishlist_id = db.Column(db.Integer, db.ForeignKey("proxy_wishlists.id"), nullable=True)
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Who added this item (None = owner)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    image_url = db.Column(db.String(500))
    available_images = db.Column(db.Text)  # JSON array of image URLs scraped from product page
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="wishlist_items")
    claims = db.relationship(
        "Claim", back_populates="item", lazy="selectin", cascade="all, delete-orphan", order_by="Claim.id"
    )
    added_by = db.relationship("User", foreign_keys=[added_by_id], backref="custom_gifts_added")
    proxy_wishlist = db.relationship("ProxyWishlist", back_populates="items")

    @property
    def total_claimed(self):
        return sum(c.quantity for c in self.claims)

    @property
    def is_fully_claimed(self):
        return self.total_claimed >= self.quantity

    @property
    def remaining_quantity(self):
        return max(self.quantity - self.total_claimed, 0)

    @property
    def claimers(self):
        """Distinct users who claimed this item, in claim order."""
        seen = {}
        for claim in self.claims:
            seen.setdefault(claim.claimed_by_id, claim.claimed_by)
        return list(seen.values())

    def claims_by(self, user):
        return [c for c in self.claims if c.claimed_by_id == user.id]

    @property
    def is_custom_gift(self):
        """A gift someone added to another person's list (hidden from that person)."""
        if self.proxy_wishlist_id:
            # Items added by the proxy's delegates are regular items; anyone else's are custom gifts
            return self.added_by_id not in self.proxy_wishlist.delegate_user_ids
        return self.added_by_id is not None and self.added_by_id != self.user_id

    @property
    def is_proxy_item(self):
        return self.proxy_wishlist_id is not None

    def get_available_images(self):
        if not self.available_images:
            return []
        try:
            images = json.loads(self.available_images)
        except (json.JSONDecodeError, TypeError):
            return []
        return images if isinstance(images, list) else []

    def set_available_images(self, images):
        """Store a list of image URLs (validated; unsafe entries are dropped)."""
        from app.validation import clean_available_images

        self.available_images = clean_available_images(images or [])

    def __repr__(self):
        return f"<WishlistItem {self.name}>"


class Claim(db.Model):
    """Someone's claim on an item they will give. Stored in the historical `purchases` table."""

    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    wishlist_item_id = db.Column(db.Integer, db.ForeignKey("wishlist_items.id"), nullable=False)
    claimed_by_id = db.Column("purchased_by_id", db.Integer, db.ForeignKey("users.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    purchased = db.Column(db.Boolean, default=False)  # Has the gift been bought/ordered?
    received = db.Column(db.Boolean, default=False)  # Has the gift been received (for online orders)?
    wrapped = db.Column(db.Boolean, default=False)  # Has the gift been wrapped?
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    item = db.relationship("WishlistItem", back_populates="claims")
    claimed_by = db.relationship("User", back_populates="claims")

    def __repr__(self):
        return f"<Claim item={self.wishlist_item_id} by={self.claimed_by_id} qty={self.quantity}>"


class WishlistChange(db.Model):
    """A change to a user's own wishlist, for the daily digest. user_id is always the list owner."""

    __tablename__ = "wishlist_changes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    change_type = db.Column(db.String(50), nullable=False)  # 'added', 'updated', 'deleted'
    item_name = db.Column(db.String(200), nullable=False)
    item_id = db.Column(db.Integer)  # May be null if item was deleted
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    notified = db.Column(db.Boolean, default=False, index=True)

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
    device_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=utcnow)
    last_used = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Passkey user={self.user_id} device={self.device_name}>"


class ProxyWishlist(db.Model):
    """Proxy wishlist for people who don't have accounts yet"""

    __tablename__ = "proxy_wishlists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Display name like "Lynn"
    email = db.Column(db.String(120), index=True)  # Optional email for auto-association
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    created_by = db.relationship("User", backref="proxy_wishlists_created")
    items = db.relationship("WishlistItem", back_populates="proxy_wishlist")
    delegates = db.relationship(
        "WishlistDelegate", back_populates="proxy_wishlist", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def delegate_user_ids(self):
        return {d.user_id for d in self.delegates}

    def delegate_record(self, user):
        if not user:
            return None
        return next((d for d in self.delegates if d.user_id == user.id), None)

    def is_delegate(self, user):
        return self.delegate_record(user) is not None

    def can_manage(self, user):
        """Creator, admin or delegate"""
        if not user:
            return False
        if user.is_admin or user.id == self.created_by_id:
            return True
        return self.is_delegate(user)

    def __repr__(self):
        return f"<ProxyWishlist {self.name} email={self.email}>"


class WishlistDelegate(db.Model):
    """Delegate access for proxy wishlists - allows users to manage wishlists on behalf of others"""

    __tablename__ = "wishlist_delegates"

    id = db.Column(db.Integer, primary_key=True)
    proxy_wishlist_id = db.Column(db.Integer, db.ForeignKey("proxy_wishlists.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    can_add_items = db.Column(db.Boolean, default=True, nullable=False)
    can_edit_items = db.Column(db.Boolean, default=True, nullable=False)
    can_remove_items = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref="delegate_for_wishlists")
    proxy_wishlist = db.relationship("ProxyWishlist", back_populates="delegates")

    def __repr__(self):
        return f"<WishlistDelegate user={self.user_id} proxy_wishlist={self.proxy_wishlist_id}>"


class Invite(db.Model):
    """Single-use registration invite. Only a SHA-256 of the token is stored."""

    __tablename__ = "invites"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    note = db.Column(db.String(200))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked = db.Column(db.Boolean, default=False, nullable=False)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    used_by = db.relationship("User", foreign_keys=[used_by_id])

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create(cls, created_by, note="", days=None):
        """Create an invite; returns (invite, raw_token). The raw token is not recoverable later."""
        days = days or current_app.config["INVITE_EXPIRY_DAYS"]
        token = secrets.token_urlsafe(32)
        invite = cls(
            token_hash=cls.hash_token(token),
            note=(note or "").strip()[:200] or None,
            created_by_id=created_by.id if created_by else None,
            expires_at=utcnow() + timedelta(days=days),
        )
        db.session.add(invite)
        return invite, token

    @classmethod
    def find_usable(cls, token):
        if not token or not isinstance(token, str) or len(token) > 100:
            return None
        invite = cls.query.filter_by(token_hash=cls.hash_token(token)).first()
        return invite if invite is not None and invite.is_usable else None

    @property
    def is_usable(self):
        return not self.revoked and self.used_at is None and self.expires_at > utcnow()

    @property
    def status(self):
        if self.used_at:
            return "used"
        if self.revoked:
            return "revoked"
        if self.expires_at <= utcnow():
            return "expired"
        return "open"

    def mark_used(self, user):
        self.used_at = utcnow()
        self.used_by_id = user.id

    def __repr__(self):
        return f"<Invite {self.id} {self.status}>"


class GiftHistory(db.Model):
    """An item from a past season's lists, saved when an admin starts a new Christmas (claimed or not).

    Rows belong to the recipient (a user, or a proxy wishlist until that person joins). Denormalised on purpose:
    the original item and claims are deleted when the season is closed.
    """

    __tablename__ = "gift_history"

    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.String(20), nullable=False, index=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_proxy_id = db.Column(
        db.Integer, db.ForeignKey("proxy_wishlists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_name = db.Column(db.String(100), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer, nullable=False, default=1)  # how many were wished for
    claimed_quantity = db.Column(db.Integer, nullable=False, default=0, server_default="0")  # 0 = nobody claimed it
    givers = db.Column(db.String(500))  # display names of whoever claimed it, comma-separated
    was_surprise = db.Column(db.Boolean, nullable=False, default=False)
    archived_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def __repr__(self):
        return f"<GiftHistory {self.season} {self.item_name!r} -> {self.recipient_name}>"
