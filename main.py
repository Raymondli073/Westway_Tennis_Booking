"""
Westway Tennis Monitor — entry point.

Usage:
  python main.py              # run once immediately (ignores time window)
  python main.py --schedule   # run every 30 min, 09:00–00:00 UK time
  python main.py --schedule --interval 15  # custom interval in minutes
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import pytz
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("monitor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

UK_TZ       = pytz.timezone("Europe/London")
WINDOW_START = 9   # 09:00
WINDOW_END   = 24  # midnight (00:00 = end of day)


def _get_config() -> dict:
    required = ["EA_EMAIL", "EA_PASSWORD", "SMTP_USER", "SMTP_PASSWORD"]
    config = {k: os.getenv(k, "") for k in required}
    config["NOTIFY_EMAIL"] = os.getenv("NOTIFY_EMAIL", "Raymondli073@gmail.com")
    config["DAYS_AHEAD"]   = os.getenv("DAYS_AHEAD", "7")
    config["HEADLESS"]     = os.getenv("HEADLESS", "true")

    missing = [k for k in required if not config[k]]
    if missing:
        logger.error(f"Missing required env vars: {', '.join(missing)}")
        logger.error("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    return config


def _in_window() -> bool:
    """Return True if current UK time is within 09:00–00:00."""
    now_uk = datetime.now(UK_TZ)
    hour = now_uk.hour
    return WINDOW_START <= hour < WINDOW_END  # 9 <= hour <= 23


def run_once(config: dict) -> None:
    from app.monitor import run_check
    run_check(config)


def _scheduled_job(config: dict) -> None:
    """Job executed by APScheduler — skips silently outside the time window."""
    if not _in_window():
        now_uk = datetime.now(UK_TZ)
        logger.info(f"Outside active window (UK time: {now_uk.strftime('%H:%M')}) — skipping.")
        return
    from app.monitor import run_check
    run_check(config)


def run_scheduled(config: dict, interval_minutes: int) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone=UK_TZ)
    scheduler.add_job(
        lambda: _scheduled_job(config),
        trigger="interval",
        minutes=interval_minutes,
        id="westway_check",
        max_instances=1,
        coalesce=True,
    )

    logger.info(f"Scheduler started — every {interval_minutes} min, active 09:00–00:00 UK time.")
    logger.info("Press Ctrl+C to stop.\n")

    # Run immediately on startup if within window
    if _in_window():
        logger.info("Within active window — running initial check now.")
        from app.monitor import run_check
        run_check(config)
    else:
        now_uk = datetime.now(UK_TZ)
        logger.info(f"Outside active window (UK time: {now_uk.strftime('%H:%M')}) — waiting.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Monitor stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Westway Tennis Court Monitor")
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run on a repeating schedule (09:00–00:00 UK time) instead of once",
    )
    parser.add_argument(
        "--interval", type=int, default=30, metavar="MINUTES",
        help="Check interval in minutes (default: 30)",
    )
    args = parser.parse_args()
    cfg  = _get_config()

    if args.schedule:
        run_scheduled(cfg, args.interval)
    else:
        run_once(cfg)
