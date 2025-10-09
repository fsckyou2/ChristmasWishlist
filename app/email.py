from flask import current_app, render_template
from flask_mail import Message
from app import mail
from threading import Thread


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


def send_password_reset_email(user):
    """Send password reset email"""
    token = user.generate_reset_token()
    reset_url = f"{current_app.config['APP_URL']}/auth/reset-password/{token}"

    send_email(
        subject='Reset Your Password',
        recipients=user.email,
        text_body=f'''Dear {user.name},

To reset your password, please click the following link:

{reset_url}

This link will expire in {current_app.config['PASSWORD_RESET_TOKEN_EXPIRY'] // 60} minutes.

If you did not request a password reset, please ignore this email.

Best regards,
{current_app.config['APP_NAME']} Team
''',
        html_body=f'''
<p>Dear {user.name},</p>
<p>To reset your password, please click the following link:</p>
<p><a href="{reset_url}">Reset Password</a></p>
<p>This link will expire in {current_app.config['PASSWORD_RESET_TOKEN_EXPIRY'] // 60} minutes.</p>
<p>If you did not request a password reset, please ignore this email.</p>
<p>Best regards,<br>
{current_app.config['APP_NAME']} Team</p>
'''
    )


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
