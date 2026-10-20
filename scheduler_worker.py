#!/usr/bin/env python3
"""
Standalone scheduler worker for periodic tasks (the daily digest).

Runs as its own service so jobs execute once, not once per gunicorn worker.

Usage:
    python scheduler_worker.py
"""

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    from app import create_app
    from app.scheduler import add_jobs

    def shutdown(signum, frame):
        logger.info("Received signal %s, shutting down scheduler...", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    app = create_app()
    scheduler = BlockingScheduler()
    add_jobs(scheduler, app)

    logger.info("Scheduler worker running.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
