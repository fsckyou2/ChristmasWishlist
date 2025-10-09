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

        # This is the endpoint that my_list_table.html tries to call
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

        # Should have either success or error field
        assert "error" in data or "title" in data or "name" in data, "Response should have error or product data"

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
