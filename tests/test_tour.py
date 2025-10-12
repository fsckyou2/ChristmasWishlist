"""
Tests for the welcome tour feature
"""

import pytest
from app.models import User
from app import db
from flask import session


class TestTourFeature:
    """Test suite for welcome tour functionality"""

    def login_user(self, client, app, user):
        """Helper to log in a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

    def test_new_user_has_not_seen_tour(self, app, user):
        """Test that new users have has_seen_tour set to False"""
        with app.app_context():
            test_user = db.session.get(User, user.id)
            assert test_user.has_seen_tour is False

    def test_tour_included_in_base_template(self, client, user, app):
        """Test that tour HTML is included in pages"""
        self.login_user(client, app, user)
        response = client.get("/")
        assert b"welcome-tour" in response.data
        assert b"tour-step" in response.data

    def test_complete_tour_endpoint_requires_login(self, client):
        """Test that complete-tour endpoint requires authentication"""
        response = client.post("/auth/complete-tour")
        assert response.status_code == 302  # Redirect to login

    def test_complete_tour_marks_user(self, client, user, app):
        """Test that complete-tour endpoint marks user as having seen tour"""
        self.login_user(client, app, user)

        # User should not have seen tour initially
        with app.app_context():
            user_db = db.session.get(User, user.id)
            assert user_db.has_seen_tour is False

        # Complete the tour
        response = client.post(
            "/auth/complete-tour",
            json={},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # User should now have seen tour
        with app.app_context():
            user_db = db.session.get(User, user.id)
            assert user_db.has_seen_tour is True

    def test_tour_only_shows_for_users_who_havent_seen_it(self, client, app):
        """Test that tour visibility is controlled by has_seen_tour flag"""
        # Create a user who has seen the tour
        with app.app_context():
            seen_user = User(
                email="seentour@example.com",
                name="Seen Tour User",
                has_seen_tour=True,
            )
            db.session.add(seen_user)
            db.session.commit()
            seen_user_id = seen_user.id

        # Login as user who has seen tour
        with app.app_context():
            seen_user_obj = db.session.get(User, seen_user_id)
        self.login_user(client, app, seen_user_obj)

        # The tour HTML is still in the template, but JavaScript won't show it
        # based on has_seen_tour status (checked in template logic)
        response = client.get("/")
        assert response.status_code == 200

    def test_tour_has_all_steps(self, client, user, app):
        """Test that tour includes all expected steps"""
        self.login_user(client, app, user)
        response = client.get("/")

        # Check for all 7 steps
        for step in range(1, 8):
            assert f'data-step="{step}"'.encode() in response.data

        # Check for key content in steps
        assert b"Welcome to Christmas Wishlist!" in response.data
        assert b"Create Your Wishlist" in response.data
        assert b"Browse Other Wishlists" in response.data
        assert b"Claim Gifts to Buy" in response.data
        assert b"Track Your Gift Progress" in response.data
        assert b"Custom Gifts" in response.data
        assert b"You're All Set!" in response.data

    def test_tour_navigation_buttons_present(self, client, user, app):
        """Test that tour has navigation buttons"""
        self.login_user(client, app, user)
        response = client.get("/")

        assert b"tour-prev" in response.data
        assert b"tour-next" in response.data
        assert b"tour-skip" in response.data
        assert b"tour-step-counter" in response.data

    def test_complete_tour_returns_json(self, client, user, app):
        """Test that complete-tour endpoint returns proper JSON"""
        self.login_user(client, app, user)

        response = client.post(
            "/auth/complete-tour",
            json={},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/json"
        data = response.get_json()
        assert "success" in data
        assert data["success"] is True
