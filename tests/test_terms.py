"""One word per idea: render real pages and emails as different people and fail on retired wording.

The approved vocabulary lives in docs/GLOSSARY.md. Code/URL names (proxy, delegate, /auth/login, ...) are fine;
only text a person reads is checked.
"""

import html
import re

import pytest
from flask import g

from app import db
from app.models import Claim, Invite, ProxyWishlist, User, WishlistChange, WishlistDelegate, WishlistItem

# Phrases people must never read again (case-sensitive where the word is also a normal English word).
RETIRED = [
    r"\bUnclaim",
    r"\bunclaim",
    r"Claim Gift",
    r"Claim Item",
    r"You Claimed",
    r"Fully Claimed",
    r"[Cc]ustom [Gg]ift",
    r"[Pp]roxy",
    r"Non-User",
    r"Pending Account",
    r"[Dd]elegate",
    r"Manage Wishlists",
    r"Wishlists I Manage",
    r"My Gifts for Others",
    r"My Claims",
    r"Merge with",
    r"Registration Invites",
    r"\bPurchased\b",
    r"(?<!I've )\bReceived\b",
    r"\bAcquired\b",
    r"Card View",
    r"Table View",
    r"Wishlist Updates from Your Family",
    r"Gifts You've Received",
    r"Gifts I've Received",
    r"Start a New Season",
    r"\bLogin\b",
    r"\bLogout\b",
    r"\bSign (in|out)\b",
    r"won't see",
    r"will NOT see",
]
RETIRED_RE = re.compile("|".join(f"(?:{p})" for p in RETIRED))


def visible_text(page):
    """Text a person can read: drop scripts/styles/tags, keep alt/title/placeholder/data-confirm attribute text."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    attrs = re.findall(r'(?:alt|title|placeholder|data-confirm|aria-label|value)="([^"]*)"', page)
    text = re.sub(r"(?s)<[^>]+>", " ", page)
    return html.unescape(text + " " + " ".join(attrs))


def assert_clean(label, page):
    hits = sorted({m.group(0) for m in RETIRED_RE.finditer(visible_text(page))})
    assert not hits, f"{label}: retired wording {hits}"


@pytest.fixture(autouse=True)
def fresh_user_per_request(app):
    @app.before_request
    def _forget_cached_user():
        g.pop("_login_user", None)


def make_user(name, email, admin=False):
    user = User(email=email, name=name, is_admin=admin)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user):
    client.post(f"/auth/magic-login/{user.generate_magic_link_token()}")


@pytest.fixture
def world(app):
    kid = make_user("Westley", "kid@example.com")
    aunt = make_user("Aunt Rebecca", "aunt@example.com")
    admin = make_user("John", "john@example.com", admin=True)
    proxy = ProxyWishlist(name="Lynn", created_by_id=admin.id)
    db.session.add(proxy)
    db.session.flush()
    db.session.add(WishlistDelegate(proxy_wishlist_id=proxy.id, user_id=aunt.id))
    items = [
        WishlistItem(user_id=kid.id, name="LEGO", quantity=1, url="https://example.com/lego"),
        WishlistItem(user_id=kid.id, name="Socks", quantity=3),
        WishlistItem(user_id=kid.id, added_by_id=aunt.id, name="Bike", quantity=1),
        WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=aunt.id, name="Quilt", quantity=1),
        WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=admin.id, name="Scarf", quantity=2),
    ]
    db.session.add_all(items)
    db.session.flush()
    db.session.add_all(
        [
            Claim(wishlist_item_id=items[0].id, claimed_by_id=aunt.id, quantity=1),
            Claim(wishlist_item_id=items[1].id, claimed_by_id=admin.id, quantity=1),
            Claim(wishlist_item_id=items[2].id, claimed_by_id=aunt.id, quantity=1),
        ]
    )
    Invite.create(created_by=admin, note="Cousin")
    db.session.add(WishlistChange(user_id=kid.id, change_type="added", item_name="LEGO"))
    db.session.commit()
    return {"kid": kid, "aunt": aunt, "admin": admin, "proxy": proxy, "items": items}


def pages_for(w):
    kid, aunt, admin, proxy, items = w["kid"], w["aunt"], w["admin"], w["proxy"], w["items"]
    return {
        "anon": ["/", "/auth/login", "/auth/login-username", "/auth/register"],
        "kid": [
            "/",
            "/wishlist/my-list",
            "/wishlist/my-list/table",
            "/wishlist/add",
            "/auth/settings",
            "/passkey/manage",
            "/wishlist/all-users",
            f"/wishlist/view/{aunt.id}",
        ],
        "aunt": [
            f"/wishlist/view/{kid.id}",
            f"/wishlist/view-proxy/{proxy.id}",
            "/wishlist/my-claims",
            f"/wishlist/claim/{items[1].id}",
            f"/wishlist/add-custom-gift/{kid.id}",
            f"/wishlist/add-to-proxy/{proxy.id}",
            "/wishlist/delegate-wishlists",
            f"/wishlist/manage-delegate/{proxy.id}",
            f"/wishlist/delegate/add-item/{proxy.id}",
            f"/wishlist/delegate/edit-item/{items[3].id}",
            f"/wishlist/edit/{items[2].id}",
        ],
        "admin": [
            "/admin/dashboard",
            "/admin/users",
            f"/admin/user/{kid.id}",
            "/admin/items",
            "/admin/claims",
            "/admin/proxy-wishlists",
            f"/admin/proxy-wishlist/{proxy.id}/merge",
            f"/admin/proxy-wishlist/{proxy.id}/delegates",
            "/admin/invites",
            "/admin/season",
            "/wishlist/create-proxy-wishlist",
            f"/wishlist/edit-proxy/{proxy.id}",
            f"/admin/user/{kid.id}/edit",
            f"/admin/item/{items[0].id}/edit",
        ],
    }


def test_pages_use_only_glossary_words(app, world):
    for who, paths in pages_for(world).items():
        client = app.test_client()
        if who != "anon":
            login(client, world[who])
        for path in paths:
            response = client.get(path)
            expected = 403 if path == "/auth/register" else 200  # invite-only: shows "Invitation Required"
            assert response.status_code == expected, f"{who} {path} -> {response.status_code}"
            assert_clean(f"{who} {path}", response.get_data(as_text=True))


def test_flash_messages_use_only_glossary_words(app, world):
    aunt, kid, items = world["aunt"], world["kid"], world["items"]
    client = app.test_client()
    login(client, aunt)
    flows = [
        client.post(f"/wishlist/claim/{items[1].id}", data={"quantity": 1}, follow_redirects=True),
        client.post(f"/wishlist/add-custom-gift/{kid.id}", data={"name": "Kite", "quantity": 1}, follow_redirects=True),
    ]
    claim = Claim.query.filter_by(claimed_by_id=aunt.id, wishlist_item_id=items[1].id).first()
    flows.append(client.post(f"/wishlist/unclaim/{claim.id}", follow_redirects=True))
    for response in flows:
        assert_clean("flash", response.get_data(as_text=True))


def test_emails_use_only_glossary_words(app, world, monkeypatch):
    import app.email as email_mod

    sent = []
    monkeypatch.setattr(
        email_mod, "send_email", lambda subject, to, text, html_body: sent.append((subject, text, html_body))
    )
    email_mod.send_magic_link_email(world["kid"])
    email_mod.send_welcome_email(world["kid"])
    email_mod.send_daily_wishlist_digest()
    email_mod.send_season_open_email(2026)
    assert len(sent) >= 4
    for subject, text, html_body in sent:
        assert_clean(f"email {subject!r}", f"{subject}\n{text}\n{html_body}")
    assert any(s == "What's new on the family wishlists" for s, _, _ in sent)


def test_every_email_is_signed_by_santa(app, world, monkeypatch):
    import app.email as email_mod

    sent = []
    monkeypatch.setattr(email_mod, "send_email", lambda subject, to, text, html_body: sent.append((text, html_body)))
    email_mod.send_magic_link_email(world["kid"])
    email_mod.send_welcome_email(world["kid"])
    email_mod.send_daily_wishlist_digest()
    email_mod.send_season_open_email(2026)
    assert len(sent) >= 4
    for text, html_body in sent:
        assert text.rstrip().endswith(("- Santa 🎅", "Ho ho ho,\nSanta 🎅"))  # the season email has its own sign-off
        assert "Santa 🎅" in html_body
        assert "Team" not in text and "Best regards" not in text


def test_privacy_phrase_uses_cant(app, world):
    client = app.test_client()
    login(client, world["aunt"])
    page = visible_text(client.get(f"/wishlist/view/{world['kid'].id}").get_data(as_text=True))
    assert "Westley can't see" in page
    form = visible_text(client.get(f"/wishlist/add-custom-gift/{world['kid'].id}").get_data(as_text=True))
    assert "hidden from Westley" in form
