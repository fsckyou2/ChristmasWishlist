from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, WishlistItem, Purchase

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You must be an administrator to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    total_users = User.query.count()
    total_items = WishlistItem.query.count()
    total_purchases = Purchase.query.count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_items = WishlistItem.query.order_by(WishlistItem.created_at.desc()).limit(10).all()

    stats = {
        'total_users': total_users,
        'total_items': total_items,
        'total_purchases': total_purchases
    }

    return render_template('admin/dashboard.html', stats=stats,
                         recent_users=recent_users, recent_items=recent_items)


@bp.route('/users')
@login_required
@admin_required
def users():
    """View all users"""
    all_users = User.query.order_by(User.name).all()
    return render_template('admin/users.html', users=all_users)


@bp.route('/user/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View user details"""
    user = User.query.get_or_404(user_id)
    wishlist_items = WishlistItem.query.filter_by(user_id=user_id).all()
    purchases = Purchase.query.filter_by(purchased_by_id=user_id).all()

    return render_template('admin/view_user.html', user=user,
                         wishlist_items=wishlist_items, purchases=purchases)


@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        new_email = request.form.get('email', '').strip()

        if not new_name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        if not new_email:
            flash('Email cannot be empty.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user.id:
            flash('Email address is already in use.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        user.name = new_name
        user.email = new_email
        db.session.commit()

        flash(f'User details updated successfully.', 'success')
        return redirect(url_for('admin.view_user', user_id=user_id))

    return render_template('admin/edit_user.html', user=user)


@bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get_or_404(user_id)

    # Prevent removing admin from self
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'warning')
        return redirect(url_for('admin.users'))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {status} for {user.name}.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting self
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'warning')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} has been deleted.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/user/<int:user_id>/send-login-link', methods=['POST'])
@login_required
@admin_required
def send_user_login_link(user_id):
    """Send magic link login email to user"""
    user = User.query.get_or_404(user_id)
    from app.email import send_magic_link_email

    send_magic_link_email(user)
    flash(f'Login link sent to {user.email}.', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@bp.route('/user/<int:user_id>/impersonate')
@login_required
@admin_required
def impersonate(user_id):
    """Impersonate a user"""
    user = User.query.get_or_404(user_id)

    # Cannot impersonate self
    if user.id == current_user.id:
        flash('You cannot impersonate yourself.', 'warning')
        return redirect(url_for('admin.users'))

    # Store original admin user ID in session
    session['original_admin_id'] = current_user.id
    session['impersonate_user_id'] = user_id

    flash(f'Now impersonating {user.name}. Click "Stop Impersonating" to return.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/stop-impersonate')
@login_required
def stop_impersonate():
    """Stop impersonating a user"""
    if 'original_admin_id' in session:
        session.pop('original_admin_id')
        session.pop('impersonate_user_id')
        flash('Stopped impersonating user.', 'info')
    return redirect(url_for('admin.dashboard'))


@bp.route('/items')
@login_required
@admin_required
def items():
    """View all wishlist items"""
    all_items = WishlistItem.query.order_by(WishlistItem.created_at.desc()).all()
    return render_template('admin/items.html', items=all_items)


@bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_item(item_id):
    """Delete a wishlist item"""
    item = WishlistItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f'Item "{item.name}" has been deleted.', 'success')
    return redirect(url_for('admin.items'))


@bp.route('/purchases')
@login_required
@admin_required
def purchases():
    """View all purchases"""
    all_purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template('admin/purchases.html', purchases=all_purchases)
