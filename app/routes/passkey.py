from flask import Blueprint, request, jsonify, session, current_app, render_template
from flask_login import login_required, current_user, login_user
from app import db
from app.models import Passkey
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

bp = Blueprint("passkey", __name__, url_prefix="/passkey")


@bp.route("/register-begin", methods=["POST"])
@login_required
def register_begin():
    """Begin passkey registration"""
    try:
        # Get device name from request
        data = request.get_json()
        device_name = data.get("device_name", "My Device")

        # Get RP (Relying Party) info from config
        rp_id = current_app.config.get("WEBAUTHN_RP_ID", "localhost")
        rp_name = current_app.config.get("APP_NAME", "Christmas Wishlist")

        # Get user's existing credentials to exclude
        existing_credentials = []
        for passkey in current_user.passkeys:
            existing_credentials.append(PublicKeyCredentialDescriptor(id=passkey.credential_id))

        # Use email or username for passkey user_name (required field)
        user_name = current_user.email or current_user.username or f"user_{current_user.id}"

        # Generate registration options
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=str(current_user.id).encode(),
            user_name=user_name,
            user_display_name=current_user.name,
            exclude_credentials=existing_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )

        # Store challenge in session
        session["passkey_challenge"] = options.challenge
        session["passkey_device_name"] = device_name

        return options_to_json(options)

    except Exception as e:
        current_app.logger.error(f"Passkey registration begin error: {str(e)}")
        return jsonify({"error": "Failed to begin registration"}), 500


@bp.route("/register-complete", methods=["POST"])
@login_required
def register_complete():
    """Complete passkey registration"""
    try:
        data = request.get_json()
        challenge = session.get("passkey_challenge")
        device_name = session.get("passkey_device_name", "My Device")

        if not challenge:
            return jsonify({"error": "No challenge found"}), 400

        # Get RP info
        rp_id = current_app.config.get("WEBAUTHN_RP_ID", "localhost")
        # Use the actual request origin to handle both HTTP and HTTPS
        origin = request.url_root.rstrip("/")

        # Verify the registration response
        verification = verify_registration_response(
            credential=data,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
        )

        # Store the passkey
        passkey = Passkey(
            user_id=current_user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            device_name=device_name,
        )
        db.session.add(passkey)
        db.session.commit()

        # Clear session
        session.pop("passkey_challenge", None)
        session.pop("passkey_device_name", None)

        return jsonify({"success": True, "passkey_id": passkey.id, "device_name": passkey.device_name})

    except Exception as e:
        current_app.logger.error(f"Passkey registration complete error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/login-begin", methods=["POST"])
def login_begin():
    """Begin passkey authentication"""
    try:
        # Get RP info
        rp_id = current_app.config.get("WEBAUTHN_RP_ID", "localhost")

        # Generate authentication options
        options = generate_authentication_options(
            rp_id=rp_id,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge in session
        session["passkey_login_challenge"] = options.challenge

        return options_to_json(options)

    except Exception as e:
        current_app.logger.error(f"Passkey login begin error: {str(e)}")
        return jsonify({"error": "Failed to begin login"}), 500


@bp.route("/login-complete", methods=["POST"])
def login_complete():
    """Complete passkey authentication"""
    try:
        data = request.get_json()
        challenge = session.get("passkey_login_challenge")

        if not challenge:
            return jsonify({"error": "No challenge found"}), 400

        # Get the credential ID from the response (it's in rawId as base64url)
        raw_id = data.get("rawId")
        if not raw_id:
            return jsonify({"error": "No credential ID"}), 400

        # Convert base64url to bytes
        import base64

        # Add padding if needed
        raw_id_padded = raw_id + "=" * (4 - len(raw_id) % 4)
        credential_id_bytes = base64.urlsafe_b64decode(raw_id_padded)

        # Find the passkey
        passkey = Passkey.query.filter_by(credential_id=credential_id_bytes).first()

        if not passkey:
            return jsonify({"error": "Passkey not found"}), 404

        # Get RP info
        rp_id = current_app.config.get("WEBAUTHN_RP_ID", "localhost")
        # Use the actual request origin to handle both HTTP and HTTPS
        origin = request.url_root.rstrip("/")

        # Verify the authentication response
        verification = verify_authentication_response(
            credential=data,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
        )

        # Update sign count
        passkey.sign_count = verification.new_sign_count
        from datetime import datetime

        passkey.last_used = datetime.utcnow()
        db.session.commit()

        # Log the user in
        login_user(passkey.user)

        # Clear session
        session.pop("passkey_login_challenge", None)

        return jsonify({"success": True, "user_name": passkey.user.name})

    except Exception as e:
        current_app.logger.error(f"Passkey login complete error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/list", methods=["GET"])
@login_required
def list_passkeys():
    """List user's passkeys"""
    passkeys = [
        {
            "id": p.id,
            "device_name": p.device_name,
            "created_at": p.created_at.isoformat(),
            "last_used": p.last_used.isoformat() if p.last_used else None,
        }
        for p in current_user.passkeys
    ]

    return jsonify({"passkeys": passkeys})


@bp.route("/delete/<int:passkey_id>", methods=["DELETE"])
@login_required
def delete_passkey(passkey_id):
    """Delete a passkey"""
    passkey = Passkey.query.filter_by(id=passkey_id, user_id=current_user.id).first()

    if not passkey:
        return jsonify({"error": "Passkey not found"}), 404

    db.session.delete(passkey)
    db.session.commit()

    return jsonify({"success": True})


@bp.route("/manage")
@login_required
def manage():
    """Passkey management page"""
    return render_template("passkey/manage.html")
