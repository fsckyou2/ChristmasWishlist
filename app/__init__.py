from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import os

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)

    # Configure for reverse proxy support
    # This handles X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host headers
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,      # Number of proxy servers in front (X-Forwarded-For)
        x_proto=1,    # Trust X-Forwarded-Proto
        x_host=1,     # Trust X-Forwarded-Host
        x_prefix=1    # Trust X-Forwarded-Prefix (for subpath deployments)
    )

    # Load configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///wishlist.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Session cookie security for HTTPS behind reverse proxy
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Prefer X-Forwarded-Proto for URL generation
    app.config['PREFERRED_URL_SCHEME'] = os.getenv('PREFERRED_URL_SCHEME', 'http')

    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.mailgun.org')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    # App configuration
    app.config['APP_NAME'] = os.getenv('APP_NAME', 'Christmas Wishlist')
    app.config['APP_URL'] = os.getenv('APP_URL', 'http://localhost:5000')
    app.config['PASSWORD_RESET_TOKEN_EXPIRY'] = int(os.getenv('PASSWORD_RESET_TOKEN_EXPIRY', 3600))
    app.config['MAGIC_LINK_TOKEN_EXPIRY'] = int(os.getenv('MAGIC_LINK_TOKEN_EXPIRY', 1800))

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Import and register blueprints
    from app.routes import auth, wishlist, admin, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(wishlist.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(main.bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create admin user if it doesn't exist
        from app.models import User
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if admin_email and admin_password:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(
                    email=admin_email,
                    name='Administrator',
                    is_admin=True
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()

    return app
