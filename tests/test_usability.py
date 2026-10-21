"""Staying signed in, the passkey offer, one-tap claiming, and the admin new-season reset."""

import pytest
from flask import g

from app import db, services
from app.models import Claim, GiftHistory, ProxyWishlist, User, WishlistChange, WishlistItem


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
    token = user.generate_magic_link_token()
    response = client.post(f"/auth/magic-login/{token}")
    assert response.status_code == 302
    return response


@pytest.fixture
def family(app):
    kid = make_user("Westley", "kid@example.com")
    aunt = make_user("Aunt Rebecca", "aunt@example.com")
    uncle = make_user("Uncle Fred", "uncle@example.com")
    admin = make_user("John", "john@example.com", admin=True)
    lego = WishlistItem(user_id=kid.id, name="LEGO", quantity=1)
    socks = WishlistItem(user_id=kid.id, name="Socks", quantity=3)
    book = WishlistItem(user_id=kid.id, name="Book", quantity=1)
    bike = WishlistItem(user_id=kid.id, added_by_id=aunt.id, name="Bike", quantity=1)
    db.session.add_all([lego, socks, book, bike])
    db.session.flush()
    db.session.add_all(
        [
            Claim(wishlist_item_id=lego.id, claimed_by_id=aunt.id, quantity=1),
            Claim(wishlist_item_id=socks.id, claimed_by_id=uncle.id, quantity=2),
            Claim(wishlist_item_id=bike.id, claimed_by_id=aunt.id, quantity=1),
        ]
    )
    db.session.commit()
    return {"kid": kid, "aunt": aunt, "uncle": uncle, "admin": admin, "lego": lego, "socks": socks, "book": book}


class TestStaySignedIn:
    def test_magic_link_login_sets_remember_cookie(self, client, family):
        response = login(client, family["kid"])
        cookies = response.headers.getlist("Set-Cookie")
        assert any(c.startswith("remember_token=") and "HttpOnly" in c for c in cookies)

    def test_password_login_remembers_by_default(self, client, family):
        kid = family["kid"]
        kid.username = "westley"
        kid.set_password("password123")
        db.session.commit()
        response = client.post(
            "/auth/login-username", data={"username": "westley", "password": "password123", "remember_me": "y"}
        )
        assert any(c.startswith("remember_token=") for c in response.headers.getlist("Set-Cookie"))
        from app.forms import UsernamePasswordLoginForm

        assert UsernamePasswordLoginForm.remember_me.kwargs["default"] is True

    def test_remember_cookie_lasts_the_season(self, app):
        assert app.config["REMEMBER_COOKIE_DURATION"].days >= 90
        assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True

    def test_logout_clears_remember_cookie(self, client, family):
        login(client, family["kid"])
        response = client.post("/auth/logout")
        assert any(c.startswith("remember_token=;") for c in response.headers.getlist("Set-Cookie"))


class TestPasskeyOffer:
    def test_offer_shown_once_after_email_login_and_dismissable(self, client, family):
        login(client, family["kid"])
        assert b'id="passkey-offer"' in client.get("/wishlist/my-list").data
        assert client.post("/passkey/dismiss-offer").status_code == 204
        assert b'id="passkey-offer"' not in client.get("/wishlist/my-list").data

    def test_no_offer_without_fresh_login(self, client, family):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(family["kid"].id)
        assert b'id="passkey-offer"' not in client.get("/wishlist/my-list").data


class TestOneTapClaim:
    def test_single_item_has_one_tap_claim_button(self, client, family):
        login(client, family["uncle"])
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        book = family["book"]
        assert f'action="/wishlist/claim/{book.id}"' in html
        assert f'id="item-{book.id}"' in html

    def test_one_tap_claim_returns_to_the_card(self, client, family):
        login(client, family["uncle"])
        book = family["book"]
        response = client.post(f"/wishlist/claim/{book.id}", data={"quantity": 1})
        assert response.status_code == 302
        assert response.location.endswith(f"/wishlist/view/{family['kid'].id}#item-{book.id}")
        assert Claim.query.filter_by(wishlist_item_id=book.id, claimed_by_id=family["uncle"].id).count() == 1
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        assert "You're getting this" in html and ">Undo</button>" in html

    def test_multi_quantity_item_links_to_quantity_picker(self, client, family):
        mittens = WishlistItem(user_id=family["kid"].id, name="Mittens", quantity=2)
        db.session.add(mittens)
        db.session.commit()
        login(client, family["aunt"])
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        assert "I'll get this (2 left)" in html
        # Socks has exactly one left, so it gets the one-tap button
        assert f'action="/wishlist/claim/{family["socks"].id}"' in html

    def test_undo_needs_no_confirmation_and_returns_to_card(self, client, family):
        login(client, family["aunt"])
        claim = Claim.query.filter_by(wishlist_item_id=family["lego"].id).one()
        html = client.get(f"/wishlist/view/{family['kid'].id}").get_data(as_text=True)
        undo_form = html.split(f'/wishlist/unclaim/{claim.id}"')[1].split("</form>")[0]
        assert "data-confirm" not in undo_form
        response = client.post(f"/wishlist/unclaim/{claim.id}")
        assert response.location.endswith(f"#item-{family['lego'].id}")
        assert db.session.get(Claim, claim.id) is None

    def test_cannot_claim_more_than_remaining(self, client, family):
        login(client, family["aunt"])
        client.post(f"/wishlist/claim/{family['lego'].id}", data={"quantity": 1})
        assert Claim.query.filter_by(wishlist_item_id=family["lego"].id).count() == 1


class TestNewSeason:
    def test_preview_counts(self, family):
        assert services.season_preview() == {
            "total_items": 4,
            "claimed_items": 3,  # LEGO, Socks (2 of 3), the surprise Bike
            "unclaimed_items": 1,  # Book
            "claims": 3,
            "lists": 1,
        }

    def test_close_season_archives_and_clears(self, family):
        changes_before = WishlistChange.query.count()
        services.close_season("2025")
        db.session.commit()

        assert WishlistItem.query.count() == 0  # every list starts fresh, claimed or not
        assert Claim.query.count() == 0
        assert WishlistChange.query.count() == changes_before  # nothing for the digest

        history = {h.item_name: h for h in GiftHistory.query.all()}
        assert set(history) == {"LEGO", "Socks", "Bike", "Book"}  # unclaimed items are archived too
        assert (history["Socks"].quantity, history["Socks"].claimed_quantity) == (3, 2)
        assert history["Socks"].givers == "Uncle Fred"
        assert (history["Book"].claimed_quantity, history["Book"].givers) == (0, None)
        assert history["Bike"].was_surprise and history["Bike"].givers == "Aunt Rebecca"
        assert all(h.season == "2025" and h.recipient_user_id == family["kid"].id for h in history.values())

    def test_admin_page_requires_typed_confirmation(self, client, family):
        login(client, family["admin"])
        page = client.get("/admin/season").get_data(as_text=True)
        assert "<strong>All 4</strong> item(s)" in page and "<strong>3</strong> claimed item(s)" in page
        assert "built-in method" not in page
        assert f'value="Start Christmas {int(services.default_season_label()) + 1}"' in page
        client.post("/admin/season", data={"season": "2025", "confirm": "2024", "notify": ""})
        assert WishlistItem.query.count() == 4  # nothing happened

    def test_admin_closes_season_and_optionally_emails(self, client, family, monkeypatch):
        import app.email as email_mod

        sent = []
        monkeypatch.setattr(email_mod, "send_email", lambda subject, to, text, html: sent.append(to))
        login(client, family["admin"])
        response = client.post("/admin/season", data={"season": "2025", "confirm": "2025", "notify": "y"})
        assert response.status_code == 302
        assert WishlistItem.query.count() == 0 and GiftHistory.query.count() == 4
        assert sorted(sent) == sorted(u.email for u in User.query.all())

    def test_only_admins_can_close_season(self, client, family):
        login(client, family["aunt"])
        client.post("/admin/season", data={"season": "2025", "confirm": "2025"})
        assert GiftHistory.query.count() == 0

    def test_archive_is_kept_but_never_shown_on_the_site(self, client, app, family):
        services.close_season("2025")
        db.session.commit()
        assert GiftHistory.query.filter_by(recipient_user_id=family["kid"].id).count() == 4

        login(client, family["kid"])
        assert client.get("/wishlist/received").status_code == 404
        html = client.get("/wishlist/my-list").get_data(as_text=True)
        assert "Received" not in html and "Aunt Rebecca" not in html and "Uncle Fred" not in html

        admin = app.test_client()
        login(admin, family["admin"])
        page = admin.get("/admin/season").get_data(as_text=True)
        assert "Christmas 2025: 4 item(s) archived" in page  # counts only, for the admin
        assert "LEGO" not in page and "Aunt Rebecca" not in page

    def test_proxy_history_follows_the_person_when_they_join(self, client, family, invite):
        proxy = ProxyWishlist(name="Lynn", created_by_id=family["admin"].id)
        db.session.add(proxy)
        db.session.flush()
        quilt = WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=family["admin"].id, name="Quilt", quantity=1)
        db.session.add(quilt)
        db.session.flush()
        db.session.add(Claim(wishlist_item_id=quilt.id, claimed_by_id=family["aunt"].id, quantity=1))
        db.session.commit()
        services.close_season("2025")
        db.session.commit()
        assert GiftHistory.query.filter_by(recipient_proxy_id=proxy.id).count() == 1

        client.post(
            "/auth/register-username",
            data={"name": "Lynn", "username": "lynn", "password": "password123", "confirm_password": "password123"},
        )
        lynn = User.query.filter_by(username="lynn").one()
        assert GiftHistory.query.filter_by(recipient_user_id=lynn.id, item_name="Quilt").count() == 1

    def test_season_must_be_a_year(self, client, family):
        login(client, family["admin"])
        client.post("/admin/season", data={"season": "last", "confirm": "last"})
        assert WishlistItem.query.count() == 4

    def test_season_email_names_the_new_christmas(self, client, family, monkeypatch):
        import app.email as email_mod

        sent = []
        monkeypatch.setattr(email_mod, "send_email", lambda subject, to, text, html: sent.append((subject, text)))
        login(client, family["admin"])
        client.post("/admin/season", data={"season": "2025", "confirm": "2025", "notify": "y"})
        subject, text = sent[0]
        assert subject.endswith(": Time to update your list!")
        assert "The family wishlists are open for Christmas 2026! 🎄" in text
        assert text.rstrip().endswith("Ho ho ho,\nSanta 🎅")

    def test_default_season_label(self):
        from datetime import datetime

        assert services.default_season_label(datetime(2026, 10, 20)) == "2025"
        assert services.default_season_label(datetime(2026, 12, 27)) == "2026"


class TestHelpersSeeClaimsNotClaimers:
    @pytest.fixture
    def kid_list(self, family):
        from app.models import WishlistDelegate

        proxy = ProxyWishlist(name="Lynn", created_by_id=family["admin"].id)
        db.session.add(proxy)
        db.session.flush()
        db.session.add(WishlistDelegate(proxy_wishlist_id=proxy.id, user_id=family["kid"].id))
        doll = WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=family["kid"].id, name="Doll", quantity=1)
        paints = WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=family["kid"].id, name="Paints", quantity=2)
        db.session.add_all([doll, paints])
        db.session.flush()
        db.session.add_all(
            [
                Claim(wishlist_item_id=doll.id, claimed_by_id=family["uncle"].id, quantity=1),
                Claim(wishlist_item_id=paints.id, claimed_by_id=family["uncle"].id, quantity=1),
            ]
        )
        db.session.commit()
        return proxy

    def test_helper_sees_claimed_status_without_names(self, client, family, kid_list):
        login(client, family["kid"])  # Westley is a helper on Lynn's list
        html = client.get(f"/wishlist/view-proxy/{kid_list.id}").get_data(as_text=True)
        assert "✓ Claimed" in html and "1 of 2 claimed" in html
        assert "Uncle Fred" not in html
        assert "you see what's claimed but not who claimed it" in html

    def test_other_givers_still_see_names(self, client, family, kid_list):
        login(client, family["aunt"])
        html = client.get(f"/wishlist/view-proxy/{kid_list.id}").get_data(as_text=True)
        assert "Claimed by Uncle Fred" in html and "by Uncle Fred" in html

    def test_list_starter_who_is_not_a_helper_sees_what_any_giver_sees(self, client, family):
        """Starting a list for someone doesn't make you a helper: you see claimers and surprises like anyone else."""
        proxy = ProxyWishlist(name="Lynn", created_by_id=family["aunt"].id)
        db.session.add(proxy)
        db.session.flush()
        doll = WishlistItem(proxy_wishlist_id=proxy.id, name="Doll", quantity=1)
        surprise = WishlistItem(proxy_wishlist_id=proxy.id, added_by_id=family["uncle"].id, name="Kite", quantity=1)
        db.session.add_all([doll, surprise])
        db.session.flush()
        db.session.add_all(
            [
                Claim(wishlist_item_id=doll.id, claimed_by_id=family["uncle"].id, quantity=1),
                Claim(wishlist_item_id=surprise.id, claimed_by_id=family["uncle"].id, quantity=1),
            ]
        )
        db.session.commit()
        login(client, family["aunt"])
        html = client.get(f"/wishlist/view-proxy/{proxy.id}").get_data(as_text=True)
        assert "Claimed by Uncle Fred" in html
        assert "Kite" in html

    def test_policy(self, family, kid_list):
        from app import policy

        doll = WishlistItem.query.filter_by(name="Doll").one()
        assert policy.can_view_claims(family["kid"], doll)
        assert not policy.can_view_claimers(family["kid"], doll)
        assert policy.can_view_claimers(family["aunt"], doll)
