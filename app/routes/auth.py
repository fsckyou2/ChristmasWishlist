from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from app.forms import RegistrationForm, LoginForm
from app.email import send_magic_link_email, send_welcome_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Passwordless user registration"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(), name=form.name.data)
        db.session.add(user)
        db.session.commit()

        # Send welcome email with login link included
        send_welcome_email(user)

        flash("Registration successful! Check your email for a welcome message with your login link.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Passwordless login - sends magic link"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            send_magic_link_email(user)
        # Always show success message to prevent email enumeration
        flash("If an account exists with that email, a login link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/login.html", form=form)


@bp.route("/magic-login/<token>")
def magic_login(token):
    """Login via magic link"""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_magic_link_token(token)
    if not user:
        flash("Invalid or expired login link.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    flash(f"Welcome, {user.name}!", "success")
    return redirect(url_for("main.index"))


@bp.route("/logout")
def logout():
    """User logout"""
    # Clear impersonation if active
    if "impersonate_user_id" in session:
        session.pop("impersonate_user_id")
        flash("Stopped impersonating user.", "info")
    else:
        logout_user()
        flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
