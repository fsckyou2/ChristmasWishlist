from flask import Blueprint, render_template, jsonify, current_app
from flask_login import current_user

from sqlalchemy import text

from app import __version__, db, policy
from app.models import User, WishlistItem

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    if current_user.is_authenticated:
        # Count items on user's wishlist (excluding custom gifts from others)
        my_items_count = len(
            policy.visible_items(current_user, WishlistItem.query.filter_by(user_id=current_user.id).all())
        )

        # Get other users
        other_users = User.query.filter(User.id != current_user.id).order_by(User.name).limit(10).all()

        return render_template("main/index.html", my_items_count=my_items_count, other_users=other_users)
    return render_template("main/index.html")


@bp.route("/healthz")
def healthz():
    """Container health check: the app is serving and the database answers."""
    db.session.execute(text("SELECT 1"))
    return "ok", 200, {"Content-Type": "text/plain", "Cache-Control": "no-store"}


@bp.route("/version")
def version():
    """Return application version"""
    return jsonify({"version": __version__, "app": current_app.config["APP_NAME"]})


@bp.route("/manifest.json")
def manifest():
    """Return PWA manifest with dynamic app name"""
    app_name = current_app.config["APP_NAME"]
    return jsonify(
        {
            "name": app_name,
            "short_name": app_name,
            "description": f"{app_name} - Share your holiday wishes",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#111827",
            "theme_color": "#dc2626",
            "icons": [
                {"src": "/static/images/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/images/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
    )
