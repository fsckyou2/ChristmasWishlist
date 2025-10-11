from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from pathlib import Path

# Load environment variables
load_dotenv()

# Version tracking
_version_file = Path(__file__).parent.parent / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


def create_app(config_name="default"):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration from config.py
    from config import config

    app.config.from_object(config[config_name])

    # Configure for reverse proxy support
    # This handles X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host headers
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,  # Number of proxy servers in front (X-Forwarded-For)
        x_proto=1,  # Trust X-Forwarded-Proto
        x_host=1,  # Trust X-Forwarded-Host
        x_prefix=1,  # Trust X-Forwarded-Prefix (for subpath deployments)
    )

    # Session cookie security for HTTPS behind reverse proxy (only if not testing)
    if not app.config.get("TESTING"):
        app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Prefer X-Forwarded-Proto for URL generation
    app.config["PREFERRED_URL_SCHEME"] = os.getenv("PREFERRED_URL_SCHEME", "http")

    # WebAuthn configuration
    app.config["WEBAUTHN_RP_ID"] = os.getenv("WEBAUTHN_RP_ID", "localhost")

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Import and register blueprints
    from app.routes import auth, wishlist, admin, main, scraper, passkey

    app.register_blueprint(auth.bp)
    app.register_blueprint(wishlist.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(scraper.bp)
    app.register_blueprint(passkey.bp)

    # Add version to template context
    @app.context_processor
    def inject_version():
        return {"app_version": __version__}

    # Create database tables
    with app.app_context():
        db.create_all()

        # Check if migrations are needed (for existing databases)
        from sqlalchemy import inspect

        inspector = inspect(db.engine)

        # Check for missing columns (added in v1.5.0)
        if "wishlist_items" in inspector.get_table_names():
            columns_info = {col["name"]: col for col in inspector.get_columns("wishlist_items")}
            missing_migrations = []

            if "available_images" not in columns_info:
                missing_migrations.append(
                    ("available_images column", "scripts/migrate_available_images.py", "image selection")
                )
            if "proxy_wishlist_id" not in columns_info:
                missing_migrations.append(
                    ("proxy_wishlist_id column", "scripts/migrate_proxy_wishlists.py", "proxy wishlist")
                )

            # Check if user_id is nullable (required for proxy wishlists)
            if "user_id" in columns_info and not columns_info["user_id"]["nullable"]:
                missing_migrations.append(
                    ("user_id nullable constraint", "scripts/migrate_user_id_nullable.py", "proxy wishlist items")
                )

            if missing_migrations:
                print("\n" + "=" * 70)
                print("⚠️  WARNING: Database migration required!")
                print("=" * 70)
                print("Your database needs the following migrations:")
                print("")
                for item, script, feature in missing_migrations:
                    print(f"  - {item} (for {feature} feature)")
                print("")
                print("Please run the migration scripts:")
                print("")
                for item, script, feature in missing_migrations:
                    print(f"  docker exec <container-name> python {script}")
                print("")
                print("Or for local development:")
                for item, script, feature in missing_migrations:
                    print(f"  python {script}")
                print("")
                print("The app will start, but some features will not work")
                print("until the migrations are complete.")
                print("=" * 70 + "\n")

        # Create admin user if it doesn't exist (passwordless)
        from app.models import User

        admin_email = os.getenv("ADMIN_EMAIL")
        admin_name = os.getenv("ADMIN_NAME")
        if admin_email:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(email=admin_email, name=admin_name, is_admin=True)
                db.session.add(admin)
                db.session.commit()

        # Initialize scheduler for daily digest emails
        from app.scheduler import init_scheduler

        init_scheduler(app)

        # Register CLI commands
        from app.cli import init_cli

        init_cli(app)

    return app
