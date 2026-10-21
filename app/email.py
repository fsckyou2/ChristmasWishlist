"""Outgoing email. Bodies are rendered from autoescaped Jinja templates in templates/email/."""

import logging
from datetime import timedelta
from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from app import db, mail
from app.models import utcnow

logger = logging.getLogger(__name__)

_CHANGE_VERBS = {
    "added": ("Added", "to their wishlist"),
    "updated": ("Updated", "on their wishlist"),
    "deleted": ("Removed", "from their wishlist"),
}


def send_async_email(app, msg):
    """Send in a background thread; failures are logged rather than lost."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception:
            logger.exception("Failed to send email %r to %s", msg.subject, msg.recipients)


def delivery_enabled():
    """False when MAIL_DELIVERY=off: emails are rendered as usual but never leave the server."""
    return bool(current_app.config.get("MAIL_DELIVERY", True))


def send_email(subject, recipients, text_body, html_body):
    if not delivery_enabled():
        logger.info("Email delivery is off; not sending %r to %s", subject, recipients)
        return False
    msg = Message(
        subject=subject,
        recipients=recipients if isinstance(recipients, list) else [recipients],
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
    )
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg), daemon=False).start()
    return True


def _render(template, **context):
    context.setdefault("app_name", current_app.config["APP_NAME"])
    context.setdefault("app_url", current_app.config["APP_URL"])
    return render_template(f"email/{template}.txt", **context), render_template(f"email/{template}.html", **context)


def _login_context(user):
    token = user.generate_magic_link_token()
    if not token:
        return None
    return {
        "user": user,
        "login_url": f"{current_app.config['APP_URL']}/auth/magic-login/{token}",
        "expiry_minutes": current_app.config["MAGIC_LINK_TOKEN_EXPIRY"] // 60,
    }


def send_magic_link_email(user):
    """Send magic link login email (no-op for username-only users)"""
    if not user.email:
        return False
    context = _login_context(user)
    if context is None:
        return False
    text, html = _render("magic_link", **context)
    return send_email("Your magic link", user.email, text, html)


def send_welcome_email(user):
    """Send welcome email to new users with magic login link"""
    if not user.email:
        return False
    context = _login_context(user)
    if context is None:
        return False
    text, html = _render("welcome", **context)
    return send_email(f"Welcome to {current_app.config['APP_NAME']}!", user.email, text, html)


def send_daily_wishlist_digest():
    """Email each user the last day's changes to *other* people's own lists.

    WishlistChange rows are only written for items on the owner's own list that the owner can see (see
    app.services.record_change), so the digest never mentions custom gifts or claims.
    """
    from app.models import User, WishlistChange

    since = utcnow() - timedelta(days=1)
    pending = (
        WishlistChange.query.filter(WishlistChange.created_at >= since, WishlistChange.notified == False)  # noqa: E712
        .order_by(WishlistChange.created_at.desc())
        .all()
    )
    if not pending:
        return

    owners = {u.id: u for u in User.query.filter(User.id.in_({c.user_id for c in pending})).all()}

    for recipient in User.query.filter(User.email.isnot(None)).all():
        sections = {}
        for change in pending:
            if change.user_id == recipient.id or change.user_id not in owners:
                continue
            verb, suffix = _CHANGE_VERBS.get(change.change_type, ("Changed", "on their wishlist"))
            sections.setdefault(change.user_id, []).append(
                {"verb": verb, "suffix": suffix, "item_name": change.item_name}
            )
        if not sections:
            continue
        text, html = _render(
            "digest",
            recipient=recipient,
            sections=[(owners[uid], changes) for uid, changes in sections.items()],
        )
        send_email("What's new on the family wishlists", recipient.email, text, html)

    for change in pending:
        change.notified = True
    db.session.commit()


def render_season_open_email(user, christmas):
    """(subject, text, html) of the "lists are open" email for one person. Used for sending and for the preview."""
    text, html = _render("season_open", user=user, christmas=christmas)
    return f"{current_app.config['APP_NAME']}: Time to update your list!", text, html


def season_open_recipients():
    from app.models import User

    return User.query.filter(User.email.isnot(None)).order_by(User.name).all()


def send_season_open_email(christmas):
    """Tell everyone with an email address that lists are open. Returns how many were actually sent (0 when off)."""
    sent = 0
    for user in season_open_recipients():
        subject, text, html = render_season_open_email(user, christmas)
        sent += bool(send_email(subject, user.email, text, html))
    return sent
