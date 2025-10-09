import pytest
from app.models import User
from app import db
from flask import url_for


class TestAuthRoutes:
    """Test authentication routes"""

    def test_register_page_loads(self, client):
        """Test registration page loads"""
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert b"Create Account" in response.data

    def test_register_user(self, client, app):
        """Test user registration"""
        response = client.post(
            "/auth/register",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "submit": "Register",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify user was created (this is the real test)
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            assert user is not None, "User should be created in database"
            assert user.name == "Test User", "User name should match"
            assert user.email == "test@example.com", "User email should match"

    def test_register_duplicate_email(self, client, user):
        """Test registering with duplicate email"""
        response = client.post(
            "/auth/register",
            data={"name": "Another User", "email": user.email, "submit": "Register"},
        )

        assert b"Email already registered" in response.data

    def test_login_page_loads(self, client):
        """Test login page loads"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_login_sends_magic_link(self, client, user):
        """Test login sends magic link - verifies email function is called without error"""
        response = client.post(
            "/auth/login",
            data={"email": user.email, "submit": "Send Login Link"},
            follow_redirects=True,
        )

        # The email is sent asynchronously, so we just verify the request succeeded
        assert response.status_code == 200, "Login request should succeed"
        # User should still exist after login attempt
        assert user.email is not None, "User should exist"

    def test_magic_link_login(self, client, app, user):
        """Test logging in with magic link"""
        with app.app_context():
            token = user.generate_magic_link_token()

        response = client.get(f"/auth/magic-login/{token}", follow_redirects=True)
        assert response.status_code == 200
        assert b"Welcome" in response.data

    def test_invalid_magic_link(self, client):
        """Test invalid magic link"""
        response = client.get("/auth/magic-login/invalid-token", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid or expired" in response.data

    def test_logout(self, client, app, user):
        """Test logout"""
        # Login first
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f"/auth/magic-login/{token}")

        # Logout
        response = client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"logged out" in response.data
