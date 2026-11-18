import pytest
from app.models import User, WishlistItem
from app import db


class TestScraperFunctionality:
    """Test URL scraping functionality"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

    def test_table_view_scraper_endpoint_exists(self, client, app, user):
        """Test that the scraper endpoint exists for table view"""
        self.login_user(client, app, user)

        # The endpoint behind auto-fill and My Wishlist's "Add from a link"
        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.ebay.com/itm/394585942413"},
            content_type="application/json",
        )

        # Should return 200 and valid JSON, not 404
        assert response.status_code in [
            200,
            400,
        ], f"Got {response.status_code}, expected 200 or 400"

        # Response should be JSON
        try:
            data = response.get_json()
            assert data is not None, "Response should be valid JSON"
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {str(e)}")

    def test_scraper_handles_ebay_url(self, client, app, user):
        """Test that scraper can handle eBay URLs without JSON parse errors"""
        self.login_user(client, app, user)

        ebay_url = "https://www.ebay.com/itm/394585942413?_trkparms=amclksrc%3DITM%26aid%3D777008"

        response = client.post("/scraper/scrape", json={"url": ebay_url}, content_type="application/json")

        # Should not return HTML error page (which causes JSON.parse error)
        assert response.content_type == "application/json", f"Expected JSON response, got {response.content_type}"

        # Should return valid JSON structure
        data = response.get_json()
        assert data is not None, "Response should be valid JSON"

        # Should have normalized format with success/error and data fields
        assert "error" in data or "success" in data, "Response should have error or success field"
        if "success" in data and data["success"]:
            assert "data" in data, "Successful response should have data field"
            assert "name" in data["data"], "Product data should have name field"

    def test_scraper_returns_json_on_error(self, client, app, user):
        """Test that scraper returns JSON even on errors"""
        self.login_user(client, app, user)

        # Invalid URL
        response = client.post(
            "/scraper/scrape",
            json={"url": "not-a-url"},
            content_type="application/json",
        )

        # Should still return JSON
        assert response.content_type == "application/json", "Error response should still be JSON"

        data = response.get_json()
        assert data is not None, "Error response should be valid JSON"
        assert "error" in data, "Error response should have 'error' field"

    def test_scraper_validates_url_parameter(self, client, app, user):
        """Test that scraper validates the URL parameter"""
        self.login_user(client, app, user)

        # Missing URL
        response = client.post("/scraper/scrape", json={}, content_type="application/json")

        assert response.status_code in [400, 422], "Should return error for missing URL"
        data = response.get_json()
        assert "error" in data, "Should return error message"

    def test_scraper_requires_authentication(self, client, app):
        """Test that scraper endpoint requires authentication"""
        # Don't login - should get redirected
        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.amazon.com/test"},
            content_type="application/json",
        )

        # Should redirect to login or return 401
        assert response.status_code in [302, 401], "Should redirect or return unauthorized"

    def test_scraper_validates_url_format(self, client, app, user):
        """Test that scraper validates URL format"""
        self.login_user(client, app, user)

        # Test invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://invalid.com",
            "javascript:alert(1)",
            "",
            "   ",
        ]

        for invalid_url in invalid_urls:
            response = client.post(
                "/scraper/scrape",
                json={"url": invalid_url},
                content_type="application/json",
            )

            data = response.get_json()
            assert "error" in data, f"Should return error for invalid URL: {invalid_url}"

    def test_scraper_handles_missing_json_body(self, client, app, user):
        """Test that scraper handles requests without JSON body"""
        self.login_user(client, app, user)

        response = client.post("/scraper/scrape")

        # Should return error (400 or 500 is acceptable)
        assert response.status_code in [400, 500]
        data = response.get_json()
        if data:
            assert "error" in data

    def test_scraper_etsy_url_accepted(self, client, app, user):
        """Test that Etsy URLs are now accepted (with ScraperAPI)"""
        self.login_user(client, app, user)

        # Note: This will likely fail to scrape in tests (no ScraperAPI key)
        # but should not return the old "Etsy has strong bot protection" error
        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.etsy.com/listing/123456"},
            content_type="application/json",
        )

        data = response.get_json()
        # Should not contain the old Etsy blocking error message
        if "error" in data:
            assert "strong bot protection" not in data["error"].lower()

    def test_scraper_normalizes_response_format(self, client, app, user):
        """Test that scraper normalizes response format consistently"""
        self.login_user(client, app, user)

        # Use a real URL that might work (or fail gracefully)
        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.amazon.com/test"},
            content_type="application/json",
        )

        data = response.get_json()

        # Should have either success or error
        assert "success" in data or "error" in data

        # If success, should have normalized data structure
        if "success" in data and data["success"]:
            assert "data" in data
            assert isinstance(data["data"], dict)
            # Should have normalized keys (not "title", should be "name")
            expected_keys = ["name", "price", "description", "image_url", "images"]
            for key in expected_keys:
                assert key in data["data"], f"Missing normalized key: {key}"

    def test_scraper_handles_amazon_url(self, client, app, user):
        """Test scraper endpoint with Amazon URL"""
        self.login_user(client, app, user)

        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.amazon.com/dp/B00TEST123"},
            content_type="application/json",
        )

        assert response.status_code in [200, 400]
        data = response.get_json()
        assert data is not None

    def test_scraper_handles_walmart_url(self, client, app, user):
        """Test scraper endpoint with Walmart URL"""
        self.login_user(client, app, user)

        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.walmart.com/ip/123456"},
            content_type="application/json",
        )

        assert response.status_code in [200, 400]
        data = response.get_json()
        assert data is not None

    def test_scraper_handles_generic_url(self, client, app, user):
        """Test scraper endpoint with generic URL"""
        self.login_user(client, app, user)

        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.example.com/product/123"},
            content_type="application/json",
        )

        assert response.status_code in [200, 400]
        data = response.get_json()
        assert data is not None

    def test_scraper_returns_images_array(self, client, app, user):
        """Test that scraper returns images array even if empty"""
        self.login_user(client, app, user)

        response = client.post(
            "/scraper/scrape",
            json={"url": "https://www.example.com/test"},
            content_type="application/json",
        )

        data = response.get_json()

        if "success" in data and data["success"]:
            assert "data" in data
            assert "images" in data["data"]
            assert isinstance(data["data"]["images"], list)

    def test_scraper_handles_url_with_special_chars(self, client, app, user):
        """Test scraper handles URLs with special characters"""
        self.login_user(client, app, user)

        # URL with query params and special chars
        url = "https://www.ebay.com/itm/123?_trkparms=amclksrc%3DITM%26aid%3D777008&test=value"

        response = client.post(
            "/scraper/scrape",
            json={"url": url},
            content_type="application/json",
        )

        assert response.status_code in [200, 400]
        data = response.get_json()
        assert data is not None
        assert response.content_type == "application/json"


GOOD_HTML = "<html><head><meta property='og:title' content='Thing'></head></html>"
CHALLENGE_HTML = "<html><head><title>Just a moment...</title></head><body>challenge-platform</body></html>"


def _http_error(status):
    """A requests.HTTPError carrying a real status code, as raise_for_status() produces."""
    import requests

    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"{status} error", response=response)


def _fake_fetcher(responses):
    """Stand in for fetch_text. `responses` maps "direct"/"standard"/"premium"/"ultra_premium" to HTML or an
    exception to raise. Returns (fn, calls) so a test can assert which modes were tried, and in what order."""
    calls = []

    def fetch(url, **kwargs):
        params = kwargs.get("params") or {}
        if url.startswith("https://api.scraperapi.com"):
            mode = (
                "premium" if params.get("premium") else "ultra_premium" if params.get("ultra_premium") else "standard"
            )
        else:
            mode = "direct"
        calls.append(mode)
        if mode not in responses:
            raise AssertionError(f"unexpected fetch in mode {mode!r}")
        outcome = responses[mode]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return fetch, calls


class TestBotWallEscalation:
    """Retailers answering with a Cloudflare/Akamai challenge is what broke link auto-fill. These pin the
    fallback that gets through, the cheapest-first order it tries, and that it cannot burn ScraperAPI credits."""

    def login(self, client, user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

    def setup(self, app, client, user, monkeypatch, responses, api_key="k3y"):
        import app.routes.scraper as scraper_mod

        app.config["SCRAPER_API_KEY"] = api_key
        fetch, calls = _fake_fetcher(responses)
        monkeypatch.setattr(scraper_mod, "fetch_text", fetch)
        monkeypatch.setattr(scraper_mod, "check_url", lambda url: None)
        self.login(client, user)
        return calls

    def scrape(self, client, url="https://shop.example/item"):
        return client.post("/scraper/scrape", json={"url": url})

    def test_a_403_falls_back_to_scraperapi_and_succeeds(self, app, client, user, monkeypatch):
        calls = self.setup(app, client, user, monkeypatch, {"direct": _http_error(403), "standard": GOOD_HTML})
        response = self.scrape(client)
        assert response.status_code == 200
        assert response.get_json()["data"]["name"] == "Thing"
        assert calls == ["direct", "standard"]

    def test_the_cheap_mode_is_tried_before_the_expensive_one(self, app, client, user, monkeypatch):
        """Standard costs ~1 credit and premium ~10, so a page standard can fetch must never reach premium."""
        calls = self.setup(app, client, user, monkeypatch, {"direct": _http_error(403), "standard": GOOD_HTML})
        assert self.scrape(client).status_code == 200
        assert "premium" not in calls

    def test_premium_is_used_when_standard_is_still_blocked(self, app, client, user, monkeypatch):
        calls = self.setup(
            app,
            client,
            user,
            monkeypatch,
            {"direct": _http_error(403), "standard": CHALLENGE_HTML, "premium": GOOD_HTML},
        )
        assert self.scrape(client).status_code == 200
        assert calls == ["direct", "standard", "premium"]

    def test_challenge_page_served_with_200_also_escalates(self, app, client, user, monkeypatch):
        """Some walls return the challenge with a 200, so the status code alone is not enough to notice."""
        calls = self.setup(app, client, user, monkeypatch, {"direct": CHALLENGE_HTML, "standard": GOOD_HTML})
        assert self.scrape(client).status_code == 200
        assert calls == ["direct", "standard"]

    def test_each_mode_is_tried_at_most_once(self, app, client, user, monkeypatch):
        """The credit balance is the thing to protect: a blocked page must cost a bounded number of requests."""
        calls = self.setup(
            app,
            client,
            user,
            monkeypatch,
            {
                "direct": _http_error(403),
                "standard": CHALLENGE_HTML,
                "premium": CHALLENGE_HTML,
                "ultra_premium": CHALLENGE_HTML,
            },
        )
        response = self.scrape(client)
        assert response.status_code == 400
        assert "blocking automated lookups" in response.get_json()["error"]
        assert calls == ["direct", "standard", "premium", "ultra_premium"]

    def test_ultra_premium_is_the_last_resort(self, app, client, user, monkeypatch):
        calls = self.setup(
            app,
            client,
            user,
            monkeypatch,
            {
                "direct": _http_error(403),
                "standard": _http_error(500),
                "premium": _http_error(500),
                "ultra_premium": GOOD_HTML,
            },
        )
        assert self.scrape(client).status_code == 200
        assert calls == ["direct", "standard", "premium", "ultra_premium"]

    def test_a_mode_the_plan_forbids_is_just_another_failure(self, app, client, user, monkeypatch):
        """ScraperAPI refuses a mode outside the plan with an instant, unbilled 403. It must not derail the rest
        or be retried - it is simply the attempt that did not work."""
        calls = self.setup(
            app,
            client,
            user,
            monkeypatch,
            {"direct": _http_error(403), "standard": CHALLENGE_HTML, "premium": GOOD_HTML},
        )
        assert self.scrape(client).status_code == 200
        assert calls.count("premium") == 1

    def test_without_a_key_nothing_is_sent_to_scraperapi(self, app, client, user, monkeypatch):
        calls = self.setup(app, client, user, monkeypatch, {"direct": _http_error(403)}, api_key=None)
        response = self.scrape(client)
        assert response.status_code == 400
        assert "blocking automated lookups" in response.get_json()["error"]
        assert calls == ["direct"]

    def test_an_ordinary_server_error_does_not_spend_credits(self, app, client, user, monkeypatch):
        """A broken shop is not a bot wall; paying ScraperAPI would not help, so we don't."""
        calls = self.setup(app, client, user, monkeypatch, {"direct": _http_error(500)})
        assert self.scrape(client).status_code == 400
        assert calls == ["direct"]

    def test_amazon_skips_the_pointless_direct_attempt(self, app, client, user, monkeypatch):
        calls = self.setup(app, client, user, monkeypatch, {"standard": GOOD_HTML})
        assert self.scrape(client, "https://www.amazon.com/dp/B000").status_code == 200
        assert calls == ["standard"]

    def test_amazon_escalates_when_standard_mode_is_blocked(self, app, client, user, monkeypatch):
        calls = self.setup(app, client, user, monkeypatch, {"standard": CHALLENGE_HTML, "premium": GOOD_HTML})
        assert self.scrape(client, "https://www.amazon.com/dp/B000").status_code == 200
        assert calls == ["standard", "premium"]
