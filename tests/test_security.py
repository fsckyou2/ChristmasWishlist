"""Security and surprise-protection regression tests.

Most of these started life as proof-of-concept exploits against v3.5.2; each asserts the attack no longer works.
"""

import http.server
import json
import threading
from datetime import timedelta

import pytest
from flask import g

from app import create_app, db, policy
from app.models import Claim, Invite, ProxyWishlist, User, WishlistChange, WishlistDelegate, WishlistItem, utcnow


@pytest.fixture(autouse=True)
def fresh_user_per_request(app):
    """The test app context is shared by every request, so drop Flask-Login's cached user at each request start."""

    @app.before_request
    def _forget_cached_user():
        g.pop("_login_user", None)


def make_user(name, email, admin=False):
    user = User(email=email, name=name, is_admin=admin)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user):
    """Log `client` in via a magic link (GET shows a confirm page, POST logs in)."""
    g.pop("_login_user", None)  # the test app context is shared between clients
    token = user.generate_magic_link_token()
    response = client.post(f"/auth/magic-login/{token}")
    assert response.status_code == 302, "magic link login failed"
    g.pop("_login_user", None)


@pytest.fixture
def family(app):
    """Westley (kid), Aunt Rebecca (giver), John (admin). Westley has one item Rebecca claimed and one surprise."""
    kid = make_user("Westley", "kid@example.com")
    aunt = make_user("Aunt Rebecca", "aunt@example.com")
    admin = make_user("John", "john@example.com", admin=True)
    lego = WishlistItem(user_id=kid.id, name="LEGO Death Star", quantity=1, url="https://example.com/lego")
    surprise = WishlistItem(user_id=kid.id, added_by_id=aunt.id, name="SECRET Nintendo Switch", quantity=1)
    db.session.add_all([lego, surprise])
    db.session.flush()
    db.session.add_all(
        [
            Claim(wishlist_item_id=lego.id, claimed_by_id=aunt.id, quantity=1),
            Claim(wishlist_item_id=surprise.id, claimed_by_id=aunt.id, quantity=1),
        ]
    )
    db.session.commit()
    return {"kid": kid, "aunt": aunt, "admin": admin, "lego": lego, "surprise": surprise}


# --- Invite-only registration ----------------------------------------------------------------------------------------


class TestInvites:
    def test_register_without_invite_is_refused(self, client):
        assert client.get("/auth/register").status_code == 403
        response = client.post(
            "/auth/register-username",
            data={
                "name": "Stranger",
                "username": "stranger",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        assert response.status_code == 403
        assert User.query.filter_by(username="stranger").first() is None

    def test_invite_link_unlocks_registration_once(self, app, client):
        invite, token = Invite.create(created_by=None, note="cousin")
        db.session.commit()

        response = client.get(f"/auth/register?invite={token}")
        assert response.status_code == 302 and response.location.endswith("/auth/register")  # token dropped from URL
        assert client.get("/auth/register").status_code == 200

        data = {"name": "Cousin", "username": "cousin", "password": "password123", "confirm_password": "password123"}
        assert client.post("/auth/register-username", data=data).status_code == 302
        cousin = User.query.filter_by(username="cousin").one()
        assert db.session.get(Invite, invite.id).used_by_id == cousin.id

        # Same browser, same link: spent
        other = app.test_client()
        other.get(f"/auth/register?invite={token}")
        assert other.get("/auth/register").status_code == 403
        assert client.get("/auth/register").status_code == 403

    @pytest.mark.parametrize("state", ["expired", "revoked", "bogus"])
    def test_unusable_invites(self, client, state):
        invite, token = Invite.create(created_by=None)
        if state == "expired":
            invite.expires_at = utcnow() - timedelta(minutes=1)
        elif state == "revoked":
            invite.revoked = True
        else:
            token = "not-a-real-token"
        db.session.commit()
        client.get(f"/auth/register?invite={token}")
        assert client.get("/auth/register").status_code == 403

    def test_only_hash_is_stored(self, app):
        invite, token = Invite.create(created_by=None)
        db.session.commit()
        assert token not in (invite.token_hash, invite.note)
        assert Invite.find_usable(token) == invite

    def test_admin_creates_and_revokes_invites(self, client, family):
        login(client, family["admin"])
        response = client.post("/admin/invites", data={"note": "Grandma", "days": 7})
        assert response.status_code == 200
        assert b"/auth/register?invite=" in response.data
        invite = Invite.query.filter_by(note="Grandma").one()
        client.post(f"/admin/invites/{invite.id}/revoke")
        assert db.session.get(Invite, invite.id).revoked

    def test_non_admin_cannot_create_invites(self, client, family):
        login(client, family["aunt"])
        client.post("/admin/invites", data={"note": "x", "days": 7})
        assert Invite.query.count() == 0

    def test_cli_create_invite(self, app, family):
        result = app.test_cli_runner().invoke(args=["create-invite", "--note", "Uncle"])
        assert result.exit_code == 0 and "/auth/register?invite=" in result.output
        assert Invite.query.filter_by(note="Uncle").count() == 1

    def test_nav_has_no_public_register_link(self, client):
        assert b'href="/auth/register"' not in client.get("/").data


# --- Surprise protection ---------------------------------------------------------------------------------------------


class TestSurpriseProtection:
    def test_owner_cannot_browse_own_list_with_claims(self, client, family):
        login(client, family["kid"])
        response = client.get(f"/wishlist/view/{family['kid'].id}")
        assert response.status_code == 302 and response.location.endswith("/wishlist/my-list")
        html = client.get("/wishlist/my-list").get_data(as_text=True)
        assert "LEGO Death Star" in html
        assert "SECRET Nintendo Switch" not in html
        assert "Aunt Rebecca" not in html
        assert "Claimed" not in html

    def test_owner_table_view_hides_claims_and_surprises(self, client, family):
        login(client, family["kid"])
        html = client.get("/wishlist/my-list/table").get_data(as_text=True)
        assert "SECRET Nintendo Switch" not in html and "Aunt Rebecca" not in html

    def test_others_still_see_claims_and_custom_gifts(self, client, family):
        login(client, family["admin"])
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        assert "SECRET Nintendo Switch" in html and "Aunt Rebecca" in html

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/wishlist/edit/{id}"),
            ("post", "/wishlist/delete/{id}"),
            ("get", "/wishlist/claim/{id}"),
        ],
    )
    def test_hidden_gift_is_404_for_owner(self, client, family, method, path):
        login(client, family["kid"])
        response = getattr(client, method)(path.format(id=family["surprise"].id))
        assert response.status_code == 404
        assert db.session.get(WishlistItem, family["surprise"].id) is not None

    def test_hidden_gift_json_update_is_404_for_owner(self, client, family):
        login(client, family["kid"])
        response = client.post(f"/wishlist/update-item/{family['surprise'].id}", json={"name": "peek"})
        assert response.status_code == 404

    def test_add_item_response_does_not_reveal_hidden_match(self, client, family):
        login(client, family["kid"])
        with_match = client.post("/wishlist/add-item-from-scraped-data", json={"name": "SECRET Nintendo Switch"})
        without_match = client.post("/wishlist/add-item-from-scraped-data", json={"name": "Totally different thing"})
        assert with_match.get_json().keys() == without_match.get_json().keys()
        assert with_match.get_json()["merged"] is False
        # The giver's claim carried over, so nobody else buys it twice
        item = db.session.get(WishlistItem, with_match.get_json()["item_id"])
        assert [c.claimed_by_id for c in item.claims] == [family["aunt"].id]

    def test_digest_never_mentions_custom_gifts(self, client, family, monkeypatch):
        import app.email as email_mod

        login(client, family["aunt"])
        client.post(f"/wishlist/add-custom-gift/{family['kid'].id}", data={"name": "SECRET Bike", "quantity": 1})
        bike = WishlistItem.query.filter_by(name="SECRET Bike").one()
        client.post(f"/wishlist/edit/{bike.id}", data={"name": "SECRET Bike", "quantity": 1, "price": 99})
        client.post(f"/wishlist/update-item/{bike.id}", json={"price": 120})
        client.post(f"/wishlist/delete/{family['surprise'].id}")

        assert WishlistChange.query.filter(WishlistChange.item_name.like("SECRET%")).count() == 0

        sent = []
        monkeypatch.setattr(email_mod, "send_email", lambda *a, **kw: sent.append((a, kw)))
        email_mod.send_daily_wishlist_digest()
        assert all("SECRET" not in json.dumps(args) for args in sent)

    def test_digest_attributes_changes_to_list_owner(self, client, family):
        login(client, family["kid"])
        client.post("/wishlist/add", data={"name": "Scooter", "quantity": 1})
        change = WishlistChange.query.filter_by(item_name="Scooter").one()
        assert change.user_id == family["kid"].id

    def test_admin_pages_hide_admins_own_surprises(self, client, family):
        admin = family["admin"]
        gift = WishlistItem(user_id=admin.id, added_by_id=family["aunt"].id, name="SECRET Watch", quantity=1)
        mine = WishlistItem(user_id=admin.id, name="Socks", quantity=1)
        db.session.add_all([gift, mine])
        db.session.flush()
        db.session.add(Claim(wishlist_item_id=mine.id, claimed_by_id=family["aunt"].id, quantity=1))
        db.session.commit()

        login(client, admin)
        for path in ("/admin/items", "/admin/claims", "/admin/dashboard", f"/admin/user/{admin.id}"):
            html = client.get(path).get_data(as_text=True)
            assert "SECRET Watch" not in html, path
        claims_html = client.get("/admin/claims").get_data(as_text=True)
        assert "Socks" not in claims_html
        assert "LEGO Death Star" in claims_html  # other people's claims are still visible
        assert client.get(f"/admin/item/{gift.id}/edit").status_code == 404
        assert client.get(f"/wishlist/edit/{gift.id}").status_code == 404

    def test_impersonating_admin_sees_exactly_what_user_sees(self, client, family):
        login(client, family["admin"])
        client.post(f"/admin/user/{family['kid'].id}/impersonate")
        html = client.get("/wishlist/my-list").get_data(as_text=True)
        assert "LEGO Death Star" in html and "SECRET Nintendo Switch" not in html
        assert client.get("/admin/dashboard").status_code == 302  # admin pages are off while impersonating
        client.post("/admin/stop-impersonate")
        assert client.get("/admin/dashboard").status_code == 200

    def test_impersonation_ends_if_admin_is_demoted(self, client, family):
        login(client, family["admin"])
        client.post(f"/admin/user/{family['kid'].id}/impersonate")
        family["admin"].is_admin = False
        db.session.commit()
        html = client.get("/").get_data(as_text=True)
        assert "Impersonating Westley" not in html
        assert "Welcome back, John" in html or "John" in html


# --- Authorization ---------------------------------------------------------------------------------------------------


class TestMergeAuthorization:
    def test_random_user_cannot_merge_away_items(self, client, family):
        rando = make_user("Rando", "rando@example.com")
        other = WishlistItem(user_id=family["kid"].id, name="Book", quantity=1)
        db.session.add(other)
        db.session.commit()
        login(client, rando)
        response = client.post(
            "/wishlist/merge-items", json={"source_item_id": other.id, "target_item_id": family["lego"].id}
        )
        assert response.status_code == 403
        assert db.session.get(WishlistItem, other.id) is not None

    def test_giver_can_merge_own_custom_gift(self, client, family):
        login(client, family["aunt"])
        response = client.post(
            "/wishlist/merge-items",
            json={"source_item_id": family["surprise"].id, "target_item_id": family["lego"].id},
        )
        assert response.status_code == 200
        assert db.session.get(WishlistItem, family["surprise"].id) is None

    def test_owner_cannot_merge_hidden_gift(self, client, family):
        login(client, family["kid"])
        response = client.post(
            "/wishlist/merge-items",
            json={"source_item_id": family["surprise"].id, "target_item_id": family["lego"].id},
        )
        assert response.status_code == 404

    def test_merge_across_lists_refused(self, client, family):
        aunt_item = WishlistItem(user_id=family["aunt"].id, name="Tea", quantity=1)
        db.session.add(aunt_item)
        db.session.commit()
        login(client, family["aunt"])
        response = client.post(
            "/wishlist/merge-items", json={"source_item_id": aunt_item.id, "target_item_id": family["lego"].id}
        )
        assert response.status_code == 403


class TestPolicy:
    def test_rules(self, family):
        kid, aunt, admin = family["kid"], family["aunt"], family["admin"]
        lego, surprise = family["lego"], family["surprise"]
        assert policy.is_hidden_from(kid, surprise) and not policy.is_hidden_from(aunt, surprise)
        assert not policy.can_view_claims(kid, lego) and policy.can_view_claims(aunt, lego)
        assert policy.can_edit_item(kid, lego) and not policy.can_edit_item(aunt, lego)
        assert policy.can_edit_item(aunt, surprise) and not policy.can_edit_item(kid, surprise)
        assert policy.can_edit_item(admin, lego)
        assert not policy.can_claim(kid, lego) and policy.can_claim(aunt, lego)
        assert policy.can_merge(aunt, surprise, lego) and not policy.can_merge(admin, lego, lego)

    def test_proxy_delegate_rules(self, family):
        proxy = ProxyWishlist(name="Lynn", created_by_id=family["admin"].id)
        db.session.add(proxy)
        db.session.flush()
        db.session.add(WishlistDelegate(proxy_wishlist_id=proxy.id, user_id=family["kid"].id, can_add_items=False))
        gift = WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=family["aunt"].id, name="Quilt", quantity=1)
        db.session.add(gift)
        db.session.commit()
        assert policy.is_hidden_from(family["kid"], gift)
        assert not policy.is_hidden_from(family["aunt"], gift)
        assert not policy.delegate_permission(family["kid"], proxy, "add")
        assert policy.delegate_permission(family["kid"], proxy, "edit")
        assert policy.delegate_permission(family["admin"], proxy, "add")


# --- XSS -------------------------------------------------------------------------------------------------------------


class TestXss:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("url", "javascript:alert(1)"),
            ("url", "javascript://example.com/%0Aalert(1)"),
            ("url", "data:text/html,<script>alert(1)</script>"),
            ("image_url", '";fetch("/admin/user/1/toggle-admin");//'),
            ("image_url", "/static/../../etc/passwd"),
            ("image_url", '/"onerror="alert(1)'),
            ("quantity", "lots"),
            ("price", "nan"),
        ],
    )
    def test_json_update_rejects_unsafe_values(self, client, family, field, value):
        login(client, family["kid"])
        response = client.post(f"/wishlist/update-item/{family['lego'].id}", json={field: value})
        assert response.status_code == 400
        assert getattr(db.session.get(WishlistItem, family["lego"].id), field) != value

    def test_form_rejects_javascript_url(self, client, family):
        login(client, family["kid"])
        client.post("/wishlist/add", data={"name": "Evil", "quantity": 1, "url": "javascript:alert(1)"})
        assert WishlistItem.query.filter_by(name="Evil").count() == 0

    def test_available_images_are_sanitized(self, client, family):
        login(client, family["kid"])
        client.post(
            "/wishlist/add-item-from-scraped-data",
            json={"name": "Imgs", "images": ["https://ok.example/a.jpg", "javascript:alert(1)", "' onerror='x"]},
        )
        item = WishlistItem.query.filter_by(name="Imgs").one()
        assert item.get_available_images() == ["https://ok.example/a.jpg"]

    def test_legacy_bad_data_is_neutralised_when_rendered(self, app, client, family):
        lego = family["lego"]
        lego.url = "javascript:alert(document.domain)"
        lego.image_url = '";alert(1);//'
        db.session.commit()

        login(client, family["aunt"])
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        assert "javascript:" not in html

        admin_client = app.test_client()
        login(admin_client, family["admin"])
        html = admin_client.get(f"/admin/item/{lego.id}/edit").get_data(as_text=True)
        assert 'const currentImageUrl = "\\";alert(1);//";' in html or "\\u0022;alert(1)" in html
        assert '"";alert(1);//"' not in html

    def test_csp_and_nonced_scripts(self, client, family):
        login(client, family["kid"])
        response = client.get("/wishlist/my-list")
        csp = response.headers["Content-Security-Policy"]
        nonce = csp.split("'nonce-")[1].split("'")[0]
        html = response.get_data(as_text=True)
        assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
        assert html.count("<script") == html.count(f'nonce="{nonce}"')
        assert " onclick=" not in html and " onsubmit=" not in html
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_digest_email_html_is_escaped(self, app, family, monkeypatch):
        import app.email as email_mod

        family["kid"].name = '<a href="https://evil.example">Westley</a>'
        db.session.add(WishlistChange(user_id=family["kid"].id, change_type="added", item_name="<img src=x>"))
        db.session.commit()
        sent = []
        monkeypatch.setattr(email_mod, "send_email", lambda subject, to, text, html: sent.append(html))
        email_mod.send_daily_wishlist_digest()
        assert sent and all("<img src=x>" not in html and 'href="https://evil' not in html for html in sent)


# --- Scraper SSRF ----------------------------------------------------------------------------------------------------


class TestScraperSsrf:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/",
            "http://localhost/",
            "https://192.168.1.71:8443/api/v2.0/app",
            "http://192.168.1.71/",
            "http://10.0.0.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
            "http://0.0.0.0/",
            "https://example.com:8443/",
            "file:///etc/passwd",
            "ftp://example.com/",
        ],
    )
    def test_blocked_destinations(self, client, family, url):
        login(client, family["kid"])
        response = client.post("/scraper/scrape", json={"url": url})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_peer_address_is_rechecked_after_connect(self, monkeypatch):
        """Even if the pre-check is fooled (DNS rebinding), the connected socket's address is checked."""
        from app import net

        server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setattr(net, "check_url", lambda url: None)
            with pytest.raises(net.BlockedDestination):
                net.fetch_text(f"http://127.0.0.1:{server.server_port}/")
        finally:
            server.shutdown()

    def test_redirects_are_revalidated(self, monkeypatch):
        from app import net

        calls = []

        def fake_check(url):
            calls.append(url)
            if "169.254" in url:
                raise net.BlockedDestination("private")

        class FakeResponse:
            is_redirect = True
            url = "https://public.example/start"
            headers = {"Location": "http://169.254.169.254/latest/"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(net, "check_url", fake_check)
        monkeypatch.setattr(net.requests.Session, "get", lambda self, *a, **kw: FakeResponse())
        with pytest.raises(net.BlockedDestination):
            net.fetch_text("https://public.example/start")
        assert calls == ["https://public.example/start", "http://169.254.169.254/latest/"]

    def test_scraperapi_uses_https_and_encoded_params(self, app, client, family, monkeypatch):
        import app.routes.scraper as scraper_mod

        app.config["SCRAPER_API_KEY"] = "k3y"
        seen = {}

        def fake_fetch(url, **kwargs):
            seen["url"], seen["params"] = url, kwargs.get("params")
            return "<html><head><meta property='og:title' content='Thing'></head></html>"

        monkeypatch.setattr(scraper_mod, "fetch_text", fake_fetch)
        monkeypatch.setattr(scraper_mod, "check_url", lambda url: None)
        login(client, family["kid"])
        target = "https://www.amazon.com/dp/B000?x=1&render=true"
        client.post("/scraper/scrape", json={"url": target})
        assert seen["url"].startswith("https://api.scraperapi.com")
        assert seen["params"] == {"api_key": "k3y", "url": target}

    def test_fetch_errors_are_not_echoed(self, client, family, monkeypatch):
        import requests

        import app.routes.scraper as scraper_mod

        def boom(url, **kwargs):
            raise requests.ConnectionError("internal detail: 10.1.2.3 refused")

        monkeypatch.setattr(scraper_mod, "fetch_text", boom)
        monkeypatch.setattr(scraper_mod, "check_url", lambda url: None)
        login(client, family["kid"])
        response = client.post("/scraper/scrape", json={"url": "https://shop.example/item"})
        assert response.status_code == 400 and "10.1.2.3" not in response.get_data(as_text=True)


# --- Sessions, CSRF, rate limits -------------------------------------------------------------------------------------


class TestSessions:
    def test_magic_link_is_single_use(self, app, client, family):
        token = family["kid"].generate_magic_link_token()
        assert client.get(f"/auth/magic-login/{token}").status_code == 200  # confirm page; link not consumed
        assert client.post(f"/auth/magic-login/{token}").status_code == 302
        other = app.test_client()
        g.pop("_login_user", None)
        response = other.post(f"/auth/magic-login/{token}")
        assert response.status_code == 302 and "/auth/login" in response.location

    def test_older_links_die_after_any_login(self, app, client, family):
        old = family["kid"].generate_magic_link_token()
        login(client, family["kid"])
        assert User.verify_magic_link_token(old) is None

    def test_state_changing_gets_are_gone(self, client, family):
        login(client, family["admin"])
        assert client.get("/auth/logout").status_code == 405
        assert client.get(f"/admin/user/{family['kid'].id}/impersonate").status_code == 405
        assert client.get("/admin/stop-impersonate").status_code == 405


@pytest.fixture
def strict_app(monkeypatch):
    """The testing app with CSRF and rate limiting switched back on."""
    import config as config_module

    class StrictConfig(config_module.TestingConfig):
        WTF_CSRF_ENABLED = True
        RATELIMIT_ENABLED = True
        RATELIMIT_STORAGE_URI = "memory://"

    monkeypatch.setitem(config_module.config, "strict", StrictConfig)
    app = create_app("strict")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestCsrfAndRateLimits:
    def test_admin_form_post_without_token_is_rejected(self, strict_app):
        admin = make_user("John", "john@example.com", admin=True)
        victim = make_user("Kid", "kid@example.com")
        client = strict_app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin.id)
        response = client.post(f"/admin/user/{victim.id}/toggle-admin")
        assert response.status_code == 400
        assert not db.session.get(User, victim.id).is_admin

    def test_json_endpoint_needs_csrf_header(self, strict_app):
        user = make_user("Kid", "kid@example.com")
        item = WishlistItem(user_id=user.id, name="Thing", quantity=1)
        db.session.add(item)
        db.session.commit()
        client = strict_app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
        assert client.post(f"/wishlist/update-item/{item.id}", json={"name": "x"}).status_code == 400

        html = client.get("/wishlist/my-list").get_data(as_text=True)
        token = html.split('name="csrf-token" content="')[1].split('"')[0]
        response = client.post(f"/wishlist/update-item/{item.id}", json={"name": "x"}, headers={"X-CSRFToken": token})
        assert response.status_code == 200

    def test_password_login_is_rate_limited(self, strict_app):
        strict_app.config["WTF_CSRF_ENABLED"] = False
        client = strict_app.test_client()
        codes = [
            client.post("/auth/login-username", data={"username": "x", "password": "y"}).status_code for _ in range(12)
        ]
        assert 429 in codes


# --- Configuration ---------------------------------------------------------------------------------------------------


class TestConfig:
    @pytest.mark.parametrize("secret", ["", "dev-secret-key-change-in-production", "short"])
    def test_production_refuses_weak_secret(self, monkeypatch, secret):
        import config as config_module

        monkeypatch.setattr(config_module.ProductionConfig, "SECRET_KEY", secret)
        with pytest.raises(config_module.ConfigError):
            create_app("production")

    def test_default_config_is_production(self, monkeypatch):
        from config import config_name_from_env

        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("FLASK_ENV", raising=False)
        assert config_name_from_env() == "production"

    def test_healthz(self, client):
        assert client.get("/healthz").data == b"ok"


# --- Migrations ------------------------------------------------------------------------------------------------------


def test_migrations_build_the_model_schema(tmp_path, monkeypatch):
    """`flask init-db` on an empty database produces exactly the schema the models describe."""
    import config as config_module
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    class MigrationConfig(config_module.TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'fresh.db'}"

    monkeypatch.setitem(config_module.config, "migration-test", MigrationConfig)
    app = create_app("migration-test")
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["init-db"])
        assert result.exit_code == 0, result.output
        with db.engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
        assert diff == []
