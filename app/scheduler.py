"""Periodic jobs. Run by scheduler_worker.py in its own container, never inside gunicorn workers."""

import logging

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def send_daily_digest_job(app):
    from app.email import send_daily_wishlist_digest

    with app.app_context():
        try:
            logger.info("Starting daily wishlist digest job...")
            send_daily_wishlist_digest()
            logger.info("Daily wishlist digest job completed")
        except Exception:
            logger.exception("Error in daily digest job")


def add_jobs(scheduler, app):
    """Register all periodic jobs on `scheduler`. DAILY_DIGEST_HOUR is local time in DIGEST_TIMEZONE."""
    hour = app.config["DAILY_DIGEST_HOUR"]
    tz = app.config["DIGEST_TIMEZONE"]
    scheduler.add_job(
        func=send_daily_digest_job,
        args=[app],
        trigger=CronTrigger(hour=hour, minute=0, timezone=tz),
        id="daily_wishlist_digest",
        name="Send daily wishlist digest emails",
        replace_existing=True,
    )
    logger.info("Daily digest scheduled for %02d:00 %s", hour, tz)
