from flask import Blueprint, render_template
from flask_login import current_user
from app.models import User, WishlistItem

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    if current_user.is_authenticated:
        # Count items on user's wishlist
        my_items_count = WishlistItem.query.filter_by(user_id=current_user.id).count()

        # Get other users
        other_users = User.query.filter(User.id != current_user.id).order_by(User.name).limit(10).all()

        return render_template("main/index.html", my_items_count=my_items_count, other_users=other_users)
    return render_template("main/index.html")


@bp.route("/about")
def about():
    """About page"""
    return render_template("main/about.html")
