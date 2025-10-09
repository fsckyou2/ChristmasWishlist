"""
Scheduler for running periodic tasks like daily wishlist digest emails
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
import logging

logger = logging.getLogger(__name__)


def send_daily_digest_job():
    """Job to send daily wishlist digest emails"""
    from app.email import send_daily_wishlist_digest

    try:
        logger.info("Starting daily wishlist digest job...")
        send_daily_wishlist_digest()
        logger.info("Daily wishlist digest job completed successfully")
    except Exception as e:
        logger.error(f"Error in daily digest job: {str(e)}")


def init_scheduler(app):
    """Initialize the scheduler with the Flask app"""
    scheduler = BackgroundScheduler()

    # Get the hour to send emails from config (default to 9 AM)
    digest_hour = app.config.get('DAILY_DIGEST_HOUR', 9)

    # Schedule daily digest to run at the specified hour every day
    scheduler.add_job(
        func=send_daily_digest_job,
        trigger=CronTrigger(hour=digest_hour, minute=0),
        id='daily_wishlist_digest',
        name='Send daily wishlist digest emails',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started. Daily digest will run at {digest_hour}:00 UTC")

    return scheduler
