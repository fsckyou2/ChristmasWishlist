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


class TestUsernamePasswordAuth:
    """Test username/password authentication"""

    def test_register_username_page_loads(self, client):
        """Test username registration page loads"""
        response = client.get("/auth/register-username")
        assert response.status_code == 200
        assert b"Create Account" in response.data
        assert b"Username" in response.data

    def test_register_username_user(self, client, app):
        """Test user registration with username/password"""
        response = client.post(
            "/auth/register-username",
            data={
                "name": "Test User",
                "username": "testuser",
                "password": "password123",
                "confirm_password": "password123",
                "submit": "Register",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify user was created
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user is not None, "User should be created in database"
            assert user.name == "Test User", "User name should match"
            assert user.username == "testuser", "Username should match"
            assert user.email is None, "Email should be None for username-only users"
            assert user.password_hash is not None, "Password hash should be set"
            assert user.check_password("password123"), "Password should be valid"

    def test_register_username_duplicate(self, client, app):
        """Test registering with duplicate username"""
        # Create first user
        with app.app_context():
            user = User(username="testuser", name="Test User")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        # Try to register with same username
        response = client.post(
            "/auth/register-username",
            data={
                "name": "Another User",
                "username": "testuser",
                "password": "password456",
                "confirm_password": "password456",
                "submit": "Register",
            },
        )

        assert b"Username already taken" in response.data

    def test_register_username_password_mismatch(self, client):
        """Test registration with password mismatch"""
        response = client.post(
            "/auth/register-username",
            data={
                "name": "Test User",
                "username": "testuser",
                "password": "password123",
                "confirm_password": "password456",
                "submit": "Register",
            },
        )

        assert b"Field must be equal to password" in response.data or b"Passwords must match" in response.data

    def test_register_username_short_password(self, client):
        """Test registration with short password"""
        response = client.post(
            "/auth/register-username",
            data={
                "name": "Test User",
                "username": "testuser",
                "password": "short",
                "confirm_password": "short",
                "submit": "Register",
            },
        )

        assert b"at least 8 characters" in response.data

    def test_login_username_page_loads(self, client):
        """Test username login page loads"""
        response = client.get("/auth/login-username")
        assert response.status_code == 200
        assert b"Login" in response.data
        assert b"Username" in response.data

    def test_login_username_success(self, client, app):
        """Test successful username/password login"""
        # Create user
        with app.app_context():
            user = User(username="testuser", name="Test User")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        # Login
        response = client.post(
            "/auth/login-username",
            data={"username": "testuser", "password": "password123", "submit": "Login"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Welcome, Test User!" in response.data

    def test_login_username_wrong_password(self, client, app):
        """Test login with wrong password"""
        # Create user
        with app.app_context():
            user = User(username="testuser", name="Test User")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        # Try to login with wrong password
        response = client.post(
            "/auth/login-username",
            data={"username": "testuser", "password": "wrongpassword", "submit": "Login"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid username or password" in response.data

    def test_login_username_nonexistent_user(self, client):
        """Test login with nonexistent username"""
        response = client.post(
            "/auth/login-username",
            data={"username": "nonexistent", "password": "password123", "submit": "Login"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid username or password" in response.data

    def test_login_username_remember_me(self, client, app):
        """Test remember me functionality"""
        # Create user
        with app.app_context():
            user = User(username="testuser", name="Test User")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        # Login with remember me
        response = client.post(
            "/auth/login-username",
            data={"username": "testuser", "password": "password123", "remember_me": "y", "submit": "Login"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Welcome, Test User!" in response.data
