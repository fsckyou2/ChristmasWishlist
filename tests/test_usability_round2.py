"""Usability round 2: My Wishlist in place, Most wanted, reorder, Browse counts/badges/reminders, totals, digest
preferences, undo delete."""

import html
import json
import re
from datetime import datetime, timedelta

import pytest
from flask import g

from app import db
from app.models import (
    Claim,
    DeletedItem,
    ListVisit,
    ProxyWishlist,
    Reminder,
    User,
    WishlistChange,
    WishlistDelegate,
    WishlistItem,
)


@pytest.fixture(autouse=True)
def fresh_user_per_request(app):
    @app.before_request
    def _forget_cached_user():
        g.pop("_login_user", None)


def login(client, user):
    client.post(f"/auth/magic-login/{user.generate_magic_link_token()}")


def add(user=None, proxy=None, name="Thing", **fields):
    item = WishlistItem(
        user_id=user.id if user else None, proxy_wishlist_id=proxy.id if proxy else None, name=name, **fields
    )
    item.quantity = fields.get("quantity", 1)
    db.session.add(item)
    db.session.commit()
    return item


def names_in_order(page, names):
    positions = {name: page.index(name) for name in names}
    return sorted(names, key=positions.get)


# --- My Wishlist: one page, edit in place, Most wanted, reorder ------------------------------------------------------


def test_most_wanted_first_then_chosen_order(app, client, user):
    a, b, c = add(user, name="Alpha", position=0), add(user, name="Bravo", position=1), add(user, name="Charlie")
    c.most_wanted = True
    db.session.commit()
    login(client, user)
    page = client.get("/wishlist/my-list").get_data(as_text=True)
    assert names_in_order(page, ["Alpha", "Bravo", "Charlie"]) == ["Charlie", "Alpha", "Bravo"]
    assert "★ Most wanted" in page
    assert "/wishlist/my-list/table" not in page


def test_new_item_goes_to_the_top_of_an_ordered_list(app, client, user):
    add(user, name="Old one", position=0)
    login(client, user)
    client.post("/wishlist/add", data={"name": "Brand new", "quantity": 1})
    page = client.get("/wishlist/my-list").get_data(as_text=True)
    assert names_in_order(page, ["Old one", "Brand new"]) == ["Brand new", "Old one"]


def test_reorder_saves_the_order(app, client, user):
    a, b, c = add(user, name="Alpha"), add(user, name="Bravo"), add(user, name="Charlie")
    login(client, user)
    response = client.post("/wishlist/reorder", json={"item_ids": [b.id, c.id, a.id]})
    assert response.status_code == 200
    page = client.get("/wishlist/my-list").get_data(as_text=True)
    assert names_in_order(page, ["Alpha", "Bravo", "Charlie"]) == ["Bravo", "Charlie", "Alpha"]


def test_reorder_needs_exactly_your_visible_items(app, client, user, other_user):
    mine = add(user, name="Mine")
    theirs = add(other_user, name="Theirs")
    login(client, user)
    for ids in ([mine.id, theirs.id], [], [mine.id, mine.id], ["x"], None, [True]):
        response = client.post("/wishlist/reorder", json={"item_ids": ids})
        assert response.status_code in (400, 409), ids
    assert db.session.get(WishlistItem, theirs.id).position is None


def test_reorder_treats_a_hidden_surprise_like_any_unknown_item(app, client, user, other_user):
    """Including a hidden surprise gift's id gets the same answer as an id that doesn't exist."""
    mine = add(user, name="Mine")
    surprise = add(user, name="Secret", added_by_id=other_user.id)
    login(client, user)
    hidden = client.post("/wishlist/reorder", json={"item_ids": [mine.id, surprise.id]})
    missing = client.post("/wishlist/reorder", json={"item_ids": [mine.id, 99999]})
    assert (hidden.status_code, hidden.get_json()) == (missing.status_code, missing.get_json())
    assert client.post("/wishlist/reorder", json={"item_ids": [mine.id]}).status_code == 200
    assert db.session.get(WishlistItem, surprise.id).position is None


def test_star_and_details_via_edit_in_place(app, client, user, other_user):
    item = add(user, name="Sweater")
    login(client, user)
    response = client.post(
        f"/wishlist/update-item/{item.id}", json={"most_wanted": True, "size": "Women's M", "color": "Navy"}
    )
    assert response.status_code == 200
    item = db.session.get(WishlistItem, item.id)
    assert (item.most_wanted, item.size, item.color) == (True, "Women's M", "Navy")

    giver = app.test_client()
    login(giver, other_user)
    page = giver.get(f"/wishlist/view/{user.id}").get_data(as_text=True)
    assert "★ Most wanted" in page and "Size: Women&#39;s M" in page and "Colour: Navy" in page


def test_size_and_colour_are_limited(app, client, user):
    item = add(user, name="Sweater")
    login(client, user)
    response = client.post(f"/wishlist/update-item/{item.id}", json={"size": "x" * 51})
    assert response.status_code == 400


def test_add_form_saves_most_wanted_size_and_colour(app, client, user):
    login(client, user)
    client.post(
        "/wishlist/add", data={"name": "Boots", "quantity": 1, "most_wanted": "y", "size": "9", "color": "Brown"}
    )
    item = WishlistItem.query.filter_by(name="Boots").one()
    assert (item.most_wanted, item.size, item.color) == (True, "9", "Brown")


def test_proxy_list_shows_most_wanted_first(app, client, user, other_user):
    proxy = ProxyWishlist(name="Lynn", created_by_id=other_user.id)
    db.session.add(proxy)
    db.session.commit()
    add(proxy=proxy, name="Quilt")
    add(proxy=proxy, name="Puzzle", most_wanted=True)
    login(client, user)
    page = client.get(f"/wishlist/view-proxy/{proxy.id}").get_data(as_text=True)
    assert names_in_order(page, ["Quilt", "Puzzle"]) == ["Puzzle", "Quilt"]


def test_my_list_still_hides_surprises_and_claims(app, client, user, other_user):
    item = add(user, name="Visible")
    add(user, name="Secret surprise", added_by_id=other_user.id)
    db.session.add(Claim(wishlist_item_id=item.id, claimed_by_id=other_user.id, quantity=1))
    db.session.commit()
    login(client, user)
    page = client.get("/wishlist/my-list").get_data(as_text=True)
    assert "Visible" in page
    assert "Secret surprise" not in page and "Other User" not in page
    assert "Claimed by" not in page and "of 1 claimed" not in page and "You're getting" not in page


# --- Browse Wishlists: counts, "new" badges, reminders ---------------------------------------------------------------


@pytest.fixture
def sent_mail(monkeypatch):
    import app.email as email_mod

    sent = []
    monkeypatch.setattr(
        email_mod, "send_email", lambda subject, to, text, html_body: sent.append((subject, to, text)) or True
    )
    return sent


def test_browse_shows_how_much_is_still_available(app, client, user, other_user):
    a = add(other_user, name="One")
    add(other_user, name="Two")
    db.session.add(Claim(wishlist_item_id=a.id, claimed_by_id=user.id, quantity=1))
    db.session.commit()
    login(client, user)
    page = client.get("/wishlist/all-users").get_data(as_text=True)
    assert "1 of 2 still available" in page


def test_new_badge_counts_items_added_since_last_visit(app, client, user, other_user):
    add(other_user, name="Before")
    login(client, user)
    assert " new</span>" not in client.get("/wishlist/all-users").get_data(as_text=True)  # never visited: no badge
    client.get(f"/wishlist/view/{other_user.id}")
    assert ListVisit.query.filter_by(viewer_id=user.id, list_user_id=other_user.id).count() == 1
    visit = ListVisit.query.filter_by(viewer_id=user.id).one()
    visit.last_seen_at = visit.last_seen_at.replace(year=visit.last_seen_at.year - 1)
    db.session.commit()
    add(other_user, name="After")
    assert "2 new</span>" in client.get("/wishlist/all-users").get_data(as_text=True)
    client.get(f"/wishlist/view/{other_user.id}")
    assert " new</span>" not in client.get("/wishlist/all-users").get_data(as_text=True)


def test_own_surprise_gifts_are_not_new_to_you(app, client, user, other_user):
    add(other_user, name="Mine to give", added_by_id=user.id)
    login(client, user)
    client.get(f"/wishlist/view/{other_user.id}")
    visit = ListVisit.query.filter_by(viewer_id=user.id).one()
    visit.last_seen_at = visit.last_seen_at.replace(year=visit.last_seen_at.year - 1)
    db.session.commit()
    assert " new</span>" not in client.get("/wishlist/all-users").get_data(as_text=True)


def test_reminder_for_empty_list(app, client, user, other_user, sent_mail):
    login(client, user)
    page = client.get("/wishlist/all-users").get_data(as_text=True)
    assert "Send a reminder" in page
    response = client.post(f"/wishlist/remind/{other_user.id}", follow_redirects=True)
    assert "Reminder sent to Other User." in response.get_data(as_text=True)
    assert len(sent_mail) == 1
    subject, to, text = sent_mail[0]
    assert to == "other@example.com" and "Test User is wondering" in subject
    assert text.rstrip().endswith("Ho ho ho,\nSanta 🎅")
    # Once every few days, whoever asks
    client.post(f"/wishlist/remind/{other_user.id}")
    assert len(sent_mail) == 1
    assert "Reminder sent" in client.get("/wishlist/all-users").get_data(as_text=True)
    assert Reminder.query.count() == 1


def test_no_reminder_when_the_list_has_items(app, client, user, other_user, sent_mail):
    add(other_user, name="Something")
    login(client, user)
    assert "Send a reminder" not in client.get("/wishlist/all-users").get_data(as_text=True)
    client.post(f"/wishlist/remind/{other_user.id}")
    assert sent_mail == []


def test_surprise_gifts_dont_count_as_the_person_starting_their_list(app, client, user, other_user, sent_mail):
    add(other_user, name="Surprise", added_by_id=user.id)
    login(client, user)
    assert "Send a reminder" in client.get("/wishlist/all-users").get_data(as_text=True)


def test_reminder_respects_mail_delivery_off(app, client, user, other_user):
    app.config["MAIL_DELIVERY"] = False
    login(client, user)
    response = client.post(f"/wishlist/remind/{other_user.id}", follow_redirects=True)
    assert "Email is turned off" in response.get_data(as_text=True)
    assert Reminder.query.count() == 0


def test_reminder_needs_post_and_another_person(app, client, user, sent_mail):
    login(client, user)
    assert client.get(f"/wishlist/remind/{user.id}").status_code == 405
    client.post(f"/wishlist/remind/{user.id}")
    assert sent_mail == []
    assert User.query.count() == 1


# --- Gifts I'm Giving: totals and progress ---------------------------------------------------------------------------


def test_giving_totals_and_progress(app, client, user, other_user):
    a = add(other_user, name="Robot", price=20.0, quantity=2)
    b = add(other_user, name="Kite", price=5.5)
    c = add(other_user, name="Mystery")
    db.session.add_all(
        [
            Claim(wishlist_item_id=a.id, claimed_by_id=user.id, quantity=2, purchased=True),
            Claim(wishlist_item_id=b.id, claimed_by_id=user.id, quantity=1, purchased=True, wrapped=True),
            Claim(wishlist_item_id=c.id, claimed_by_id=user.id, quantity=1),
        ]
    )
    db.session.commit()
    login(client, user)
    page = " ".join(client.get("/wishlist/my-claims").get_data(as_text=True).split())
    assert "3 gifts for 1 person" in page
    assert "$45.50" in page  # 20 x 2 + 5.50
    assert "1 without a price not counted" in page
    assert (
        "<span data-to-buy>1</span> to buy · <span data-to-wrap>1</span> to wrap · <span data-done>1</span> done"
        in page
    )


# --- Email updates (digest preferences) ------------------------------------------------------------------------------


@pytest.fixture
def digest_mail(monkeypatch):
    import app.email as email_mod

    sent = []
    monkeypatch.setattr(
        email_mod,
        "send_email",
        lambda subject, to, text, html_body, headers=None: sent.append((to, text, headers)) or True,
    )
    return sent


MONDAY_NOON_UTC = datetime(2026, 11, 2, 17, 0)  # Monday in America/New_York
TUESDAY_NOON_UTC = datetime(2026, 11, 3, 17, 0)


def change(owner, name, when):
    db.session.add(WishlistChange(user_id=owner.id, change_type="added", item_name=name, created_at=when))
    db.session.commit()


def test_daily_digest_only_covers_changes_since_last_one(app, user, other_user, digest_mail):
    from app.email import send_daily_wishlist_digest

    change(other_user, "Old news", TUESDAY_NOON_UTC - timedelta(hours=30))
    change(other_user, "Fresh", TUESDAY_NOON_UTC - timedelta(hours=2))
    send_daily_wishlist_digest(now=TUESDAY_NOON_UTC)
    texts = [text for to, text, _ in digest_mail if to == user.email]
    assert len(texts) == 1 and "Fresh" in texts[0] and "Old news" not in texts[0]
    send_daily_wishlist_digest(now=TUESDAY_NOON_UTC + timedelta(hours=1))  # nothing new since
    assert len([to for to, _, _ in digest_mail if to == user.email]) == 1


def test_weekly_digest_goes_out_on_mondays_with_the_week(app, user, other_user, digest_mail):
    from app.email import send_daily_wishlist_digest

    user.digest_frequency = "weekly"
    db.session.commit()
    change(other_user, "Five days ago", MONDAY_NOON_UTC - timedelta(days=5))
    send_daily_wishlist_digest(now=MONDAY_NOON_UTC - timedelta(days=1))  # Sunday: nothing for weekly people
    assert not [to for to, _, _ in digest_mail if to == user.email]
    send_daily_wishlist_digest(now=MONDAY_NOON_UTC)
    texts = [text for to, text, _ in digest_mail if to == user.email]
    assert len(texts) == 1 and "Five days ago" in texts[0] and "every Monday" in texts[0]


def test_digest_off_sends_nothing(app, user, other_user, digest_mail):
    from app.email import send_daily_wishlist_digest

    user.digest_frequency = "off"
    db.session.commit()
    change(other_user, "Anything", TUESDAY_NOON_UTC - timedelta(hours=1))
    send_daily_wishlist_digest(now=TUESDAY_NOON_UTC)
    assert not [to for to, _, _ in digest_mail if to == user.email]


def test_digest_has_preferences_link_and_one_click_header(app, client, user, other_user, digest_mail):
    from app.email import preferences_token, send_daily_wishlist_digest

    change(other_user, "Anything", TUESDAY_NOON_UTC - timedelta(hours=1))
    send_daily_wishlist_digest(now=TUESDAY_NOON_UTC)
    to, text, headers = [m for m in digest_mail if m[0] == user.email][0]
    token = preferences_token(user)
    assert f"/auth/email-preferences/{token}" in text
    assert headers["List-Unsubscribe"].endswith(f"/auth/email-preferences/{token}/one-click>")
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_preferences_page_works_without_logging_in(app, client, user):
    from app.email import preferences_token

    token = preferences_token(user)
    page = client.get(f"/auth/email-preferences/{token}").get_data(as_text=True)
    assert "Email updates" in page and "Once a week (Mondays)" in page
    client.post(f"/auth/email-preferences/{token}", data={"digest_frequency": "weekly"})
    assert db.session.get(User, user.id).digest_frequency == "weekly"


def test_one_click_unsubscribe(app, client, user):
    from app.email import preferences_token

    token = preferences_token(user)
    assert client.get(f"/auth/email-preferences/{token}/one-click").status_code == 302  # GET never changes anything
    assert db.session.get(User, user.id).digest_frequency == "daily"
    response = client.post(f"/auth/email-preferences/{token}/one-click", data={"List-Unsubscribe": "One-Click"})
    assert response.status_code == 200
    assert db.session.get(User, user.id).digest_frequency == "off"


def test_tampered_preferences_token_is_404(app, client, user):
    from app.email import preferences_token

    token = preferences_token(user)
    for bad in (token[:-2] + "xx", "nope"):
        assert client.get(f"/auth/email-preferences/{bad}").status_code == 404
        assert client.post(f"/auth/email-preferences/{bad}/one-click").status_code == 404


def test_settings_page_saves_email_updates(app, client, user):
    login(client, user)
    page = client.get("/auth/settings").get_data(as_text=True)
    assert "Email updates" in page and "Every day" in page
    response = client.post("/auth/settings/email-updates", data={"digest_frequency": "off"}, follow_redirects=True)
    assert "Email updates: Off." in response.get_data(as_text=True)
    assert db.session.get(User, user.id).digest_frequency == "off"


# --- Undo instead of "are you sure?" for deleting items ---------------------------------------------------------------


def test_delete_shows_undo_and_undo_brings_back_item_and_claims(app, client, user, other_user):
    item = add(user, name="Train set", price=40.0, most_wanted=True, size="Big")
    db.session.add(Claim(wishlist_item_id=item.id, claimed_by_id=other_user.id, quantity=1, purchased=True))
    db.session.commit()
    login(client, user)
    my_list = client.get("/wishlist/my-list").get_data(as_text=True)
    assert "data-confirm" not in my_list
    page = client.post(f"/wishlist/delete/{item.id}", follow_redirects=True).get_data(as_text=True)
    assert "Deleted &#34;Train set&#34; from My Wishlist." in page and ">Undo<" in page
    assert WishlistItem.query.count() == 0 and Claim.query.count() == 0

    snapshot = DeletedItem.query.one()
    page = client.post(f"/wishlist/undo-delete/{snapshot.id}", follow_redirects=True).get_data(as_text=True)
    assert "&#34;Train set&#34; is back." in page
    restored = WishlistItem.query.one()
    assert (restored.name, restored.price, restored.most_wanted, restored.size) == ("Train set", 40.0, True, "Big")
    claim = Claim.query.one()
    assert (claim.wishlist_item_id, claim.claimed_by_id, claim.purchased) == (restored.id, other_user.id, True)
    assert DeletedItem.query.count() == 0
    # The owner still sees no sign of the claim
    page = client.get("/wishlist/my-list").get_data(as_text=True)
    assert "Other User" not in page and "Claimed by" not in page


def test_undo_forgets_the_unsent_removed_digest_entry(app, client, user):
    item = add(user, name="Puzzle")
    login(client, user)
    client.post(f"/wishlist/delete/{item.id}")
    assert WishlistChange.query.filter_by(change_type="deleted").count() == 1
    client.post(f"/wishlist/undo-delete/{DeletedItem.query.one().id}")
    assert WishlistChange.query.filter_by(change_type="deleted").count() == 0
    assert WishlistChange.query.filter_by(change_type="added").count() == 0


def test_undo_after_digest_went_out_announces_it_again(app, client, user):
    item = add(user, name="Puzzle")
    login(client, user)
    client.post(f"/wishlist/delete/{item.id}")
    WishlistChange.query.filter_by(change_type="deleted").one().notified = True
    db.session.commit()
    client.post(f"/wishlist/undo-delete/{DeletedItem.query.one().id}")
    assert WishlistChange.query.filter_by(change_type="added", item_name="Puzzle").count() == 1


def test_only_the_person_who_deleted_can_undo(app, client, user, other_user):
    item = add(user, name="Puzzle")
    login(client, user)
    client.post(f"/wishlist/delete/{item.id}")
    snapshot_id = DeletedItem.query.one().id
    stranger = app.test_client()
    login(stranger, other_user)
    page = stranger.post(f"/wishlist/undo-delete/{snapshot_id}", follow_redirects=True).get_data(as_text=True)
    assert "Too late to undo" in page
    assert WishlistItem.query.count() == 0


def test_undo_runs_out(app, client, user):
    item = add(user, name="Puzzle")
    login(client, user)
    client.post(f"/wishlist/delete/{item.id}")
    snapshot = DeletedItem.query.one()
    snapshot.deleted_at = snapshot.deleted_at - timedelta(hours=1)
    db.session.commit()
    page = client.post(f"/wishlist/undo-delete/{snapshot.id}", follow_redirects=True).get_data(as_text=True)
    assert "Too late to undo" in page
    assert WishlistItem.query.count() == 0


def test_undo_needs_post(app, client, user):
    login(client, user)
    assert client.get("/wishlist/undo-delete/1").status_code == 405


def test_helper_delete_can_be_undone(app, client, user, other_user):
    proxy = ProxyWishlist(name="Lynn", created_by_id=other_user.id)
    db.session.add(proxy)
    db.session.flush()
    db.session.add(WishlistDelegate(proxy_wishlist_id=proxy.id, user_id=user.id, can_remove_items=True))
    db.session.commit()
    item = add(proxy=proxy, name="Quilt", added_by_id=user.id)  # helpers' items are the list's own items
    login(client, user)
    response = client.post(f"/wishlist/delegate/delete-item/{item.id}")
    assert response.get_json().get("success") is True, response.get_json()
    page = client.get(f"/wishlist/manage-delegate/{proxy.id}").get_data(as_text=True)
    assert "Deleted &#34;Quilt&#34; from Lynn&#39;s Wishlist." in page and ">Undo<" in page
    client.post(f"/wishlist/undo-delete/{DeletedItem.query.one().id}")
    assert WishlistItem.query.filter_by(proxy_wishlist_id=proxy.id, name="Quilt").count() == 1


def test_old_undo_snapshots_are_purged(app, client, user):
    first, second = add(user, name="One"), add(user, name="Two")
    login(client, user)
    client.post(f"/wishlist/delete/{first.id}")
    old = DeletedItem.query.one()
    old.deleted_at = old.deleted_at - timedelta(days=2)
    db.session.commit()
    client.post(f"/wishlist/delete/{second.id}")
    assert [json.loads(d.payload)["name"] for d in DeletedItem.query.all()] == ["Two"]


# --- Navigation -------------------------------------------------------------------------------------------------------


def test_nav_marks_the_current_page_and_has_a_phone_tab_bar(app, client, user):
    login(client, user)
    page = client.get("/wishlist/my-claims").get_data(as_text=True)
    current = re.findall(r'<a [^>]*aria-current="page"[^>]*>\s*(?:<span[^>]*>[^<]*</span>)?([^<]+)<', page)
    assert [html.unescape(label.strip()) for label in current] == ["Gifts I'm Giving"] * 2  # top bar + tab bar
    assert 'aria-label="Tabs"' in page and 'data-menu="more-menu"' in page
    assert "group-hover" not in page


def test_helpers_get_a_tap_menu_and_my_wishlist_stays_top_level(app, client, user, other_user):
    proxy = ProxyWishlist(name="Lynn", created_by_id=other_user.id)
    db.session.add(proxy)
    db.session.flush()
    db.session.add(WishlistDelegate(proxy_wishlist_id=proxy.id, user_id=user.id))
    db.session.commit()
    login(client, user)
    page = client.get("/wishlist/all-users").get_data(as_text=True)
    assert 'data-menu="help-menu" aria-expanded="false"' in page
    assert page.count(f'href="/wishlist/manage-delegate/{proxy.id}"') == 2  # desktop menu + phone "More"
    assert page.count('href="/wishlist/my-list"') >= 2  # top bar + tab bar, not hidden in a menu


def test_logged_out_pages_have_no_tab_bar(app, client):
    page = client.get("/auth/login").get_data(as_text=True)
    assert 'aria-label="Tabs"' not in page and ">Log in<" in page
