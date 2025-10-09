from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from app.forms import (RegistrationForm, LoginForm, MagicLinkForm,
                       PasswordResetRequestForm, PasswordResetForm)
from app.email import send_password_reset_email, send_magic_link_email

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            name=form.name.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    """User logout"""
    # Clear impersonation if active
    if 'impersonate_user_id' in session:
        session.pop('impersonate_user_id')
        flash('Stopped impersonating user.', 'info')
    else:
        logout_user()
        flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/magic-link', methods=['GET', 'POST'])
def magic_link():
    """Request magic link login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = MagicLinkForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            send_magic_link_email(user)
        # Always show success message to prevent email enumeration
        flash('If an account exists with that email, a login link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/magic_link.html', form=form)


@bp.route('/magic-login/<token>')
def magic_login(token):
    """Login via magic link"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = User.verify_magic_link_token(token)
    if not user:
        flash('Invalid or expired login link.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user)
    flash(f'Welcome, {user.name}!', 'success')
    return redirect(url_for('main.index'))


@bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            send_password_reset_email(user)
        # Always show success message to prevent email enumeration
        flash('If an account exists with that email, password reset instructions have been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.login'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)
