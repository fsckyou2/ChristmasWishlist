import pytest
from app.models import User, Passkey
from app import db
import json


class TestPasskeyRoutes:
    """Test passkey/WebAuthn routes"""

    def login_user(self, client, app, user):
        """Helper to login a user"""
        with app.app_context():
            token = user.generate_magic_link_token()
        client.get(f'/auth/magic-login/{token}')

    def test_passkey_manage_page_requires_login(self, client):
        """Test passkey management page requires authentication"""
        response = client.get('/passkey/manage')
        assert response.status_code == 302  # Redirect to login

    def test_passkey_manage_page_loads(self, client, app, user):
        """Test passkey management page loads"""
        self.login_user(client, app, user)
        response = client.get('/passkey/manage')
        assert response.status_code == 200
        assert b'Manage Passkeys' in response.data or b'Passkey' in response.data

    def test_register_begin_requires_login(self, client):
        """Test passkey registration begin requires login"""
        response = client.post('/passkey/register-begin',
                             content_type='application/json')
        assert response.status_code == 302

    def test_register_begin_returns_options(self, client, app, user):
        """Test passkey registration begin returns options"""
        self.login_user(client, app, user)
        response = client.post('/passkey/register-begin',
                             data=json.dumps({'device_name': 'Test Device'}),
                             content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'challenge' in data
        assert 'user' in data

    def test_list_passkeys_requires_login(self, client):
        """Test listing passkeys requires login"""
        response = client.get('/passkey/list')
        assert response.status_code == 302

    def test_list_passkeys_empty(self, client, app, user):
        """Test listing passkeys when none exist"""
        self.login_user(client, app, user)
        response = client.get('/passkey/list')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'passkeys' in data
        assert len(data['passkeys']) == 0

    def test_list_passkeys_with_data(self, client, app, user):
        """Test listing passkeys when they exist"""
        # Create a passkey
        with app.app_context():
            passkey = Passkey(
                user_id=user.id,
                credential_id=b'test_credential_id',
                public_key=b'test_public_key',
                sign_count=0,
                device_name='Test Device'
            )
            db.session.add(passkey)
            db.session.commit()

        self.login_user(client, app, user)
        response = client.get('/passkey/list')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['passkeys']) == 1
        assert data['passkeys'][0]['device_name'] == 'Test Device'

    def test_delete_passkey_requires_login(self, client):
        """Test deleting passkey requires login"""
        response = client.delete('/passkey/delete/1')
        assert response.status_code == 302

    def test_delete_passkey(self, client, app, user):
        """Test deleting a passkey"""
        # Create a passkey
        with app.app_context():
            passkey = Passkey(
                user_id=user.id,
                credential_id=b'test_credential_id',
                public_key=b'test_public_key',
                sign_count=0,
                device_name='Test Device'
            )
            db.session.add(passkey)
            db.session.commit()
            passkey_id = passkey.id

        self.login_user(client, app, user)
        response = client.delete(f'/passkey/delete/{passkey_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify deletion
        with app.app_context():
            deleted_passkey = Passkey.query.get(passkey_id)
            assert deleted_passkey is None

    def test_cannot_delete_others_passkey(self, client, app, user, admin_user):
        """Test user cannot delete another user's passkey"""
        # Create passkey for admin
        with app.app_context():
            passkey = Passkey(
                user_id=admin_user.id,
                credential_id=b'admin_credential',
                public_key=b'admin_public_key',
                sign_count=0,
                device_name='Admin Device'
            )
            db.session.add(passkey)
            db.session.commit()
            passkey_id = passkey.id

        # Login as regular user
        self.login_user(client, app, user)
        response = client.delete(f'/passkey/delete/{passkey_id}')

        assert response.status_code == 404  # Not found (filtered by user_id)

    def test_login_begin_public(self, client):
        """Test passkey login begin is public"""
        response = client.post('/passkey/login-begin',
                             content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'challenge' in data


class TestPasskeyModel:
    """Test Passkey model"""

    def test_create_passkey(self, app, user):
        """Test creating a passkey"""
        with app.app_context():
            passkey = Passkey(
                user_id=user.id,
                credential_id=b'test_credential',
                public_key=b'test_public_key',
                sign_count=0,
                device_name='Test Device'
            )
            db.session.add(passkey)
            db.session.commit()

            assert passkey.id is not None
            assert passkey.user_id == user.id
            assert passkey.device_name == 'Test Device'
            assert passkey.sign_count == 0

    def test_passkey_user_relationship(self, app, user):
        """Test relationship between User and Passkey"""
        with app.app_context():
            passkey1 = Passkey(
                user_id=user.id,
                credential_id=b'cred1',
                public_key=b'key1',
                device_name='Device 1'
            )
            passkey2 = Passkey(
                user_id=user.id,
                credential_id=b'cred2',
                public_key=b'key2',
                device_name='Device 2'
            )
            db.session.add_all([passkey1, passkey2])
            db.session.commit()

            user_with_passkeys = User.query.get(user.id)
            assert len(user_with_passkeys.passkeys.all()) == 2

    def test_passkey_last_used_tracking(self, app, user):
        """Test passkey last_used timestamp"""
        from datetime import datetime

        with app.app_context():
            passkey = Passkey(
                user_id=user.id,
                credential_id=b'test_cred',
                public_key=b'test_key',
                device_name='Test'
            )
            db.session.add(passkey)
            db.session.commit()

            assert passkey.last_used is None

            # Update last_used
            passkey.last_used = datetime.utcnow()
            db.session.commit()

            updated_passkey = Passkey.query.get(passkey.id)
            assert updated_passkey.last_used is not None
