from flask import current_app, render_template
from flask_mail import Message
from app import mail, db
from threading import Thread
from datetime import datetime, timedelta


def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)


def send_email(subject, recipients, text_body, html_body):
    """Send email"""
    msg = Message(
        subject=subject,
        recipients=recipients if isinstance(recipients, list) else [recipients],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    msg.body = text_body
    msg.html = html_body

    # Send email in background thread
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


def send_magic_link_email(user):
    """Send magic link login email"""
    token = user.generate_magic_link_token()
    login_url = f"{current_app.config['APP_URL']}/auth/magic-login/{token}"

    send_email(
        subject='Your Login Link',
        recipients=user.email,
        text_body=f'''Dear {user.name},

To log in to your account, please click the following link:

{login_url}

This link will expire in {current_app.config['MAGIC_LINK_TOKEN_EXPIRY'] // 60} minutes.

If you did not request this login link, please ignore this email.

Best regards,
{current_app.config['APP_NAME']} Team
''',
        html_body=f'''
<p>Dear {user.name},</p>
<p>To log in to your account, please click the following link:</p>
<p><a href="{login_url}">Log In</a></p>
<p>This link will expire in {current_app.config['MAGIC_LINK_TOKEN_EXPIRY'] // 60} minutes.</p>
<p>If you did not request this login link, please ignore this email.</p>
<p>Best regards,<br>
{current_app.config['APP_NAME']} Team</p>
'''
    )


def send_welcome_email(user):
    """Send welcome email to new users with magic login link"""
    token = user.generate_magic_link_token()
    login_url = f"{current_app.config['APP_URL']}/auth/magic-login/{token}"
    app_url = current_app.config['APP_URL']

    send_email(
        subject=f'Welcome to {current_app.config["APP_NAME"]}!',
        recipients=user.email,
        text_body=f'''Dear {user.name},

Welcome to {current_app.config["APP_NAME"]}! 🎁

We're excited to have you join our community. You can now:

• Create and manage your Christmas wishlist
• Browse wishlists from your family
• Mark items as purchased to help coordinate gifts
• Keep the holiday spirit alive with easy gift planning

To get started, click the link below to log in to your account:

{login_url}

This link will expire in {current_app.config['MAGIC_LINK_TOKEN_EXPIRY'] // 60} minutes.

If you have any questions or need assistance, feel free to reach out.

Happy holidays!

Best regards,
{current_app.config['APP_NAME']} Team
''',
        html_body=f'''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #dc2626;">Welcome to {current_app.config["APP_NAME"]}! 🎁</h2>

    <p>Dear {user.name},</p>

    <p>We're excited to have you join our community. You can now:</p>

    <ul>
        <li>Create and manage your Christmas wishlist</li>
        <li>Browse wishlists from your family</li>
        <li>Mark items as purchased to help coordinate gifts</li>
        <li>Keep the holiday spirit alive with easy gift planning</li>
    </ul>

    <p>To get started, click the button below to log in to your account:</p>

    <p>
        <a href="{login_url}" style="display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0;">
            Log In to Your Account
        </a>
    </p>

    <p style="color: #666; font-size: 14px;">This link will expire in {current_app.config['MAGIC_LINK_TOKEN_EXPIRY'] // 60} minutes.</p>

    <p>If you have any questions or need assistance, feel free to reach out.</p>

    <p>Happy holidays!</p>

    <p style="color: #666;">
        Best regards,<br>
        {current_app.config['APP_NAME']} Team
    </p>
</div>
'''
    )


def send_daily_wishlist_digest():
    """Send daily digest emails to users about wishlist changes from other users"""
    from app.models import User, WishlistChange

    # Get all users
    all_users = User.query.all()

    # Get yesterday's date (24 hours ago)
    yesterday = datetime.utcnow() - timedelta(days=1)

    for recipient_user in all_users:
        # Get changes from OTHER users (not the recipient themselves) since yesterday
        changes = WishlistChange.query.filter(
            WishlistChange.user_id != recipient_user.id,
            WishlistChange.created_at >= yesterday,
            WishlistChange.notified == False
        ).order_by(WishlistChange.created_at.desc()).all()

        if not changes:
            # No changes to notify this user about
            continue

        # Group changes by user
        changes_by_user = {}
        for change in changes:
            if change.user_id not in changes_by_user:
                changes_by_user[change.user_id] = []
            changes_by_user[change.user_id].append(change)

        # Build email content
        text_body_lines = [f'Dear {recipient_user.name},\n']
        text_body_lines.append('Here\'s what\'s new with wishlists from your family:\n')

        html_body_parts = [f'<p>Dear {recipient_user.name},</p>']
        html_body_parts.append('<p>Here\'s what\'s new with wishlists from your family:</p>')

        for user_id, user_changes in changes_by_user.items():
            changer_user = User.query.get(user_id)
            if not changer_user:
                continue

            text_body_lines.append(f'\n{changer_user.name}:')
            html_body_parts.append(f'<h3 style="color: #dc2626; margin-top: 20px;">{changer_user.name}:</h3>')
            html_body_parts.append('<ul>')

            for change in user_changes:
                if change.change_type == 'added':
                    text_body_lines.append(f'  • Added "{change.item_name}" to their wishlist')
                    html_body_parts.append(f'<li>Added <strong>{change.item_name}</strong> to their wishlist</li>')
                elif change.change_type == 'updated':
                    text_body_lines.append(f'  • Updated "{change.item_name}" on their wishlist')
                    html_body_parts.append(f'<li>Updated <strong>{change.item_name}</strong> on their wishlist</li>')
                elif change.change_type == 'deleted':
                    text_body_lines.append(f'  • Removed "{change.item_name}" from their wishlist')
                    html_body_parts.append(f'<li>Removed <strong>{change.item_name}</strong> from their wishlist</li>')

            html_body_parts.append('</ul>')

        # Add footer
        app_url = current_app.config['APP_URL']
        text_body_lines.append(f'\nVisit {app_url} to see all wishlists.\n')
        text_body_lines.append('Happy holidays!\n')
        text_body_lines.append(f'\nBest regards,\n{current_app.config["APP_NAME"]} Team')

        html_body_parts.append(f'''
        <p>
            <a href="{app_url}" style="display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0;">
                View All Wishlists
            </a>
        </p>
        <p>Happy holidays!</p>
        <p style="color: #666;">
            Best regards,<br>
            {current_app.config["APP_NAME"]} Team
        </p>
        ''')

        # Wrap HTML in div
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            {''.join(html_body_parts)}
        </div>
        '''

        text_body = '\n'.join(text_body_lines)

        # Send the email
        send_email(
            subject='Wishlist Updates from Your Family',
            recipients=recipient_user.email,
            text_body=text_body,
            html_body=html_body
        )

    # Mark all changes as notified
    WishlistChange.query.filter(
        WishlistChange.created_at >= yesterday,
        WishlistChange.notified == False
    ).update({WishlistChange.notified: True})
    db.session.commit()
