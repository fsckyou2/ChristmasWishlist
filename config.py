import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.mailgun.org")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    # App configuration
    APP_NAME = os.getenv("APP_NAME", "Christmas Wishlist")
    APP_URL = os.getenv("APP_URL", "http://localhost:5000")
    PASSWORD_RESET_TOKEN_EXPIRY = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRY", 3600))
    MAGIC_LINK_TOKEN_EXPIRY = int(os.getenv("MAGIC_LINK_TOKEN_EXPIRY", 1800))
    DAILY_DIGEST_HOUR = int(os.getenv("DAILY_DIGEST_HOUR", 9))  # Hour (0-23, UTC) for daily digest emails


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///wishlist.db")


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
