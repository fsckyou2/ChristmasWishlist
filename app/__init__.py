import logging
import secrets
from pathlib import Path

from flask import Flask, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

_root = Path(__file__).parent.parent
_version_file = _root / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

# Tailwind's play CDN, pinned. It generates styles at runtime, hence 'unsafe-inline' for styles only.
TAILWIND_CDN = "https://cdn.tailwindcss.com/3.4.17"


def create_app(config_name=None):
    """Application factory.

    Args:
        config_name: development, testing or production. Defaults to APP_ENV / FLASK_ENV, then production.

    Schema creation, migrations and the admin bootstrap are not done here; they run once per deploy
    via `flask init-db` (see app/cli.py and docker-entrypoint.sh).
    """
    from config import config, config_name_from_env

    config_name = config_name or config_name_from_env()
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].validate(app.config)

    proxies = app.config["TRUSTED_PROXY_COUNT"]
    if proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies, x_prefix=proxies)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(_root / "migrations"), render_as_batch=True)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    from app.routes import admin, auth, main, passkey, scraper, wishlist

    for module in (auth, wishlist, admin, main, scraper, passkey):
        app.register_blueprint(module.bp)

    _register_template_helpers(app)
    _register_security_headers(app)

    from app.cli import init_cli

    init_cli(app)
    return app


def _register_template_helpers(app):
    from app.validation import display_image_url, display_url

    app.add_template_filter(display_url, "safe_href")
    app.add_template_filter(display_image_url, "safe_img")

    @app.context_processor
    def inject_globals():
        return {
            "app_version": __version__,
            "app_name": app.config["APP_NAME"],
            "csp_nonce": _csp_nonce,
            "tailwind_cdn": TAILWIND_CDN,
        }


def _csp_nonce():
    if "csp_nonce" not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def _register_security_headers(app):
    @app.after_request
    def set_security_headers(response):
        csp = "; ".join(
            [
                "default-src 'self'",
                f"script-src 'self' 'nonce-{_csp_nonce()}' {TAILWIND_CDN}",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' https: http: data:",  # product images come from anywhere
                "connect-src 'self'",
                "font-src 'self' data:",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response
