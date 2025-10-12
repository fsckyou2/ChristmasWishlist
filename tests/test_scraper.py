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
