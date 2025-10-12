#!/usr/bin/env python3
"""
Standalone scheduler worker for running periodic tasks.

This script runs as a separate service (not in gunicorn workers) to ensure
scheduled jobs only execute once, not once per worker.

Usage:
    python scheduler_worker.py
"""

import logging
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def send_daily_digest_job():
    """Job to send daily wishlist digest emails"""
    from app import create_app
    from app.email import send_daily_wishlist_digest

    # Create app context for database access
    app = create_app("production")

    with app.app_context():
        try:
            logger.info("Starting daily wishlist digest job...")
            send_daily_wishlist_digest()
            logger.info("Daily wishlist digest job completed successfully")
        except Exception as e:
            logger.error(f"Error in daily digest job: {str(e)}", exc_info=True)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down scheduler...")
    sys.exit(0)


def main():
    """Initialize and run the scheduler"""
    logger.info("=" * 70)
    logger.info("Starting Scheduler Worker")
    logger.info("=" * 70)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create app to get config
    from app import create_app

    app = create_app("production")

    # Get the hour to send emails from config (default to 9 AM local time)
    digest_hour = app.config.get("DAILY_DIGEST_HOUR", 9)

    logger.info(f"Daily digest will run at {digest_hour}:00 local time")
    logger.info("=" * 70)

    # Create blocking scheduler (runs in foreground)
    scheduler = BlockingScheduler()

    # Schedule daily digest
    scheduler.add_job(
        func=send_daily_digest_job,
        trigger=CronTrigger(hour=digest_hour, minute=0),
        id="daily_wishlist_digest",
        name="Send daily wishlist digest emails",
        replace_existing=True,
    )

    try:
        logger.info("Scheduler is running. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
