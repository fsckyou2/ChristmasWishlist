import os

from dotenv import load_dotenv

load_dotenv()

# Values that must never be used as a production SECRET_KEY
_PLACEHOLDER_SECRETS = {"", "dev-secret-key-change-in-production", "your-secret-key-here-change-in-production"}


def _env_bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class ConfigError(RuntimeError):
    """Raised at startup when the configuration is unsafe to run with."""


class Config:
    """Base configuration"""

    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///wishlist.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.mailgun.org")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    # App configuration
    APP_NAME = os.getenv("APP_NAME", "Christmas Wishlist")
    APP_URL = os.getenv("APP_URL", "http://localhost:5000").rstrip("/")
    MAGIC_LINK_TOKEN_EXPIRY = int(os.getenv("MAGIC_LINK_TOKEN_EXPIRY", 1800))
    INVITE_EXPIRY_DAYS = int(os.getenv("INVITE_EXPIRY_DAYS", 30))

    # Daily digest: hour (0-23) in DIGEST_TIMEZONE, which defaults to the container's TZ
    DAILY_DIGEST_HOUR = int(os.getenv("DAILY_DIGEST_HOUR", 9))
    DIGEST_TIMEZONE = os.getenv("DIGEST_TIMEZONE", os.getenv("TZ", "America/New_York"))

    # ScraperAPI configuration (optional, for bypassing bot detection)
    SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
    SCRAPER_MAX_BYTES = int(os.getenv("SCRAPER_MAX_BYTES", 3 * 1024 * 1024))

    # Cookies
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "http")

    # Number of reverse proxies in front of the app whose X-Forwarded-* headers we trust (0 = none)
    TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", 1))

    # WebAuthn: the relying party ID is the bare domain; the expected origin is APP_URL
    WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")

    # CSRF tokens stay valid for the whole session (pages are often left open for hours)
    WTF_CSRF_TIME_LIMIT = None

    # Rate limiting. Memory storage is per gunicorn worker, so effective limits are N x workers.
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    MAX_CONTENT_LENGTH = 1024 * 1024

    @classmethod
    def validate(cls, app_config):
        """Hook for refusing to start with unsafe settings."""


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    SECRET_KEY = Config.SECRET_KEY or "dev-secret-key-change-in-production"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SECRET_KEY = "testing-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    APP_URL = "http://localhost"
    TRUSTED_PROXY_COUNT = 0

    # Disable ScraperAPI in tests to avoid consuming API quota
    SCRAPER_API_KEY = None


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "https")

    @classmethod
    def validate(cls, app_config):
        secret = app_config.get("SECRET_KEY") or ""
        if secret in _PLACEHOLDER_SECRETS or len(secret) < 32:
            raise ConfigError(
                "SECRET_KEY must be set to a random value of at least 32 characters in production "
                '(e.g. python -c "import secrets; print(secrets.token_urlsafe(48))").'
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def config_name_from_env():
    """APP_ENV wins; FLASK_ENV is still honoured for existing deployments. Defaults to production."""
    name = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "production").strip().lower()
    if name not in config:
        raise ConfigError(f"Unknown APP_ENV {name!r}; expected one of {sorted(config)}")
    return name
