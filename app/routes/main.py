from flask import Blueprint, render_template, jsonify
from flask_login import current_user
from app.models import User, WishlistItem
from app import __version__

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    if current_user.is_authenticated:
        # Count items on user's wishlist (excluding custom gifts from others)
        my_items_count = (
            WishlistItem.query.filter_by(user_id=current_user.id)
            .filter(
                (WishlistItem.added_by_id is None) | (WishlistItem.added_by_id == current_user.id)
            )  # noqa: E711, E712
            .count()
        )

        # Get other users
        other_users = User.query.filter(User.id != current_user.id).order_by(User.name).limit(10).all()

        return render_template("main/index.html", my_items_count=my_items_count, other_users=other_users)
    return render_template("main/index.html")


@bp.route("/about")
def about():
    """About page"""
    return render_template("main/about.html")


@bp.route("/version")
def version():
    """Return application version"""
    return jsonify({"version": __version__, "app": "Christmas Wishlist"})
