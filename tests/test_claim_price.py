"""Gifts I'm Giving: the private "My price" each giver can record, and the spend totals built from it.

Privacy (who may read or write a price) lives in tests/test_security.py; this file is about the arithmetic.
"""

import re

import pytest

from app import db
from app.models import Claim, WishlistItem


def login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


@pytest.fixture
def claim(app, other_user, wishlist_item):
    """Other User is giving 2 of Test User's Test Product (listed at $29.99 each)."""
    record = Claim(wishlist_item_id=wishlist_item.id, claimed_by_id=other_user.id, quantity=2)
    db.session.add(record)
    db.session.commit()
    return record


@pytest.fixture
def giving(client, other_user):
    login(client, other_user)
    return client


def save(client, claim, price):
    return client.post(f"/wishlist/update-claim-price/{claim.id}", json={"price": price})


def stored(claim_id):
    db.session.expire_all()
    return db.session.get(Claim, claim_id).price


def unpriced_note(page):
    """The page's "N without a price not counted" tag. It is always rendered so the JS can reuse it, and carries
    the `hidden` class when there is nothing to report - so the tag itself is what a test has to look at."""
    match = re.search(r"<p[^>]*data-unpriced-note[^>]*>", page)
    assert match, "the unpriced note is missing from the page"
    return match.group(0)


def add_claim(owner, giver, name, quantity=1, price=None):
    item = WishlistItem(user_id=owner.id, name=name, quantity=quantity, price=price)
    db.session.add(item)
    db.session.flush()
    record = Claim(wishlist_item_id=item.id, claimed_by_id=giver.id, quantity=quantity)
    db.session.add(record)
    db.session.commit()
    return record


class TestSavingAPrice:
    def test_a_price_is_stored_rounded_to_cents(self, giving, claim):
        assert save(giving, claim, "12.345").status_code == 200
        assert stored(claim.id) == 12.35

    def test_a_number_works_as_well_as_a_string(self, giving, claim):
        assert save(giving, claim, 19.5).status_code == 200
        assert stored(claim.id) == 19.5

    def test_an_empty_value_clears_it(self, giving, claim):
        save(giving, claim, "12.00")
        response = save(giving, claim, "")
        assert response.status_code == 200
        assert response.get_json()["price"] is None
        assert stored(claim.id) is None

    def test_zero_is_a_real_answer_and_is_kept(self, giving, claim):
        assert save(giving, claim, "0").status_code == 200
        assert stored(claim.id) == 0.0

    @pytest.mark.parametrize("bad", ["abc", "-5", "1e400", "99999999"])
    def test_nonsense_is_refused_and_changes_nothing(self, giving, claim, bad):
        save(giving, claim, "20.00")
        response = save(giving, claim, bad)
        assert response.status_code == 400
        assert "error" in response.get_json()
        assert stored(claim.id) == 20.00

    def test_a_missing_price_field_is_refused(self, giving, claim):
        response = giving.post(f"/wishlist/update-claim-price/{claim.id}", json={})
        assert response.status_code == 400

    def test_an_unknown_claim_is_a_404(self, giving):
        assert giving.post("/wishlist/update-claim-price/999999", json={"price": "1"}).status_code == 404


class TestEffectivePrice:
    def test_the_item_price_is_the_fallback(self, claim):
        assert claim.price is None
        assert claim.effective_price == 29.99

    def test_the_givers_own_price_wins(self, app, claim):
        claim.price = 10.0
        db.session.commit()
        assert claim.effective_price == 10.0

    def test_zero_wins_too(self, app, claim):
        """A gift that cost the giver nothing must not silently fall back to the list's price."""
        claim.price = 0.0
        db.session.commit()
        assert claim.effective_price == 0.0


class TestSpendTotals:
    def test_the_total_uses_the_item_price_until_the_giver_says_otherwise(self, giving, claim):
        page = giving.get("/wishlist/my-claims").get_data(as_text=True)
        assert "$59.98" in page  # 2 x 29.99

    def test_the_total_follows_the_givers_own_price(self, giving, claim):
        save(giving, claim, "10.00")
        page = giving.get("/wishlist/my-claims").get_data(as_text=True)
        assert "$20.00" in page  # 2 x 10.00
        assert "$59.98" not in page

    def test_a_gift_with_no_price_anywhere_is_called_out(self, giving, claim, other_user, user):
        add_claim(user, other_user, "Mystery")
        note = unpriced_note(giving.get("/wishlist/my-claims").get_data(as_text=True))
        assert "hidden" not in note

    def test_pricing_it_clears_the_callout_and_adds_to_the_spend(self, giving, claim, other_user, user):
        mystery = add_claim(user, other_user, "Mystery")
        save(giving, mystery, "5.00")
        page = giving.get("/wishlist/my-claims").get_data(as_text=True)
        assert "hidden" in unpriced_note(page)
        assert "$64.98" in page  # 2 x 29.99 + 5.00

    def test_nothing_is_called_out_when_every_gift_has_a_price(self, giving, claim):
        assert "hidden" in unpriced_note(giving.get("/wishlist/my-claims").get_data(as_text=True))
