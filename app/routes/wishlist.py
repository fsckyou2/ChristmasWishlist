from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, WishlistItem, Purchase
from app.forms import WishlistItemForm, PurchaseForm
from app.scraper import ProductScraper

bp = Blueprint('wishlist', __name__, url_prefix='/wishlist')


@bp.route('/my-list')
@login_required
def my_list():
    """View current user's wishlist"""
    items = WishlistItem.query.filter_by(user_id=current_user.id).order_by(WishlistItem.created_at.desc()).all()
    return render_template('wishlist/my_list.html', items=items)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    """Add item to wishlist"""
    form = WishlistItemForm()

    if form.validate_on_submit():
        item = WishlistItem(
            user_id=current_user.id,
            name=form.name.data,
            url=form.url.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            quantity=form.quantity.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added to your wishlist!', 'success')
        return redirect(url_for('wishlist.my_list'))

    return render_template('wishlist/add_item.html', form=form)


@bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit wishlist item"""
    item = WishlistItem.query.get_or_404(item_id)

    # Check if user owns this item
    if item.user_id != current_user.id:
        flash('You can only edit your own wishlist items.', 'danger')
        return redirect(url_for('wishlist.my_list'))

    form = WishlistItemForm(obj=item)

    if form.validate_on_submit():
        item.name = form.name.data
        item.url = form.url.data
        item.description = form.description.data
        item.price = form.price.data
        item.image_url = form.image_url.data
        item.quantity = form.quantity.data
        db.session.commit()
        flash('Item updated!', 'success')
        return redirect(url_for('wishlist.my_list'))

    return render_template('wishlist/edit_item.html', form=form, item=item)


@bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete wishlist item"""
    item = WishlistItem.query.get_or_404(item_id)

    # Check if user owns this item
    if item.user_id != current_user.id:
        flash('You can only delete your own wishlist items.', 'danger')
        return redirect(url_for('wishlist.my_list'))

    db.session.delete(item)
    db.session.commit()
    flash('Item deleted from your wishlist.', 'success')
    return redirect(url_for('wishlist.my_list'))


@bp.route('/view/<int:user_id>')
@login_required
def view_user_list(user_id):
    """View another user's wishlist"""
    user = User.query.get_or_404(user_id)
    items = WishlistItem.query.filter_by(user_id=user_id).order_by(WishlistItem.created_at.desc()).all()
    return render_template('wishlist/view_list.html', user=user, items=items)


@bp.route('/purchase/<int:item_id>', methods=['GET', 'POST'])
@login_required
def purchase_item(item_id):
    """Mark item as purchased"""
    item = WishlistItem.query.get_or_404(item_id)

    # User cannot purchase their own items
    if item.user_id == current_user.id:
        flash('You cannot purchase items from your own wishlist!', 'warning')
        return redirect(url_for('wishlist.my_list'))

    form = PurchaseForm()

    # Set max quantity available
    remaining = item.quantity - item.total_purchased
    if remaining <= 0:
        flash('This item is already fully purchased.', 'info')
        return redirect(url_for('wishlist.view_user_list', user_id=item.user_id))

    if form.validate_on_submit():
        quantity = form.quantity.data

        # Validate quantity
        if quantity > remaining:
            flash(f'Only {remaining} remaining to purchase.', 'warning')
        else:
            purchase = Purchase(
                wishlist_item_id=item.id,
                purchased_by_id=current_user.id,
                quantity=quantity
            )
            db.session.add(purchase)
            db.session.commit()
            flash(f'Marked {quantity} of "{item.name}" as purchased!', 'success')
            return redirect(url_for('wishlist.view_user_list', user_id=item.user_id))

    # Pre-fill with remaining quantity
    form.quantity.data = remaining

    return render_template('wishlist/purchase_item.html', form=form, item=item, remaining=remaining)


@bp.route('/api/scrape-url', methods=['POST'])
@login_required
def scrape_url():
    """API endpoint to scrape product data from URL"""
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    data = ProductScraper.scrape_url(url)
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'Could not extract product information'}), 400


@bp.route('/all-users')
@login_required
def all_users():
    """View all users to browse their wishlists"""
    users = User.query.filter(User.id != current_user.id).order_by(User.name).all()
    return render_template('wishlist/all_users.html', users=users)
