"""
Westway Tennis Monitor — entry point.

Runs a Flask web app (subscribe/unsubscribe) and an APScheduler background
job (scrape + alert) in the same process.

Usage:
  python main.py                        # web app + scheduler (default)
  python main.py --port 8080            # custom port
  python main.py --check-now            # run one scrape check immediately, then exit
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

UK_TZ        = pytz.timezone("Europe/London")
WINDOW_START = 9    # 09:00 UK
WINDOW_END   = 24   # 00:00 (midnight)


def _get_config(port: int) -> dict:
    required = ["EA_EMAIL", "EA_PASSWORD", "SMTP_USER", "SMTP_PASSWORD"]
    config = {k: os.getenv(k, "") for k in required}
    config["NOTIFY_EMAIL"] = os.getenv("NOTIFY_EMAIL", "Raymondli073@gmail.com")
    config["DAYS_AHEAD"]   = os.getenv("DAYS_AHEAD", "7")
    config["HEADLESS"]     = os.getenv("HEADLESS", "true")
    config["BASE_URL"]     = os.getenv("BASE_URL", f"http://localhost:{port}")

    missing = [k for k in required if not config[k]]
    if missing:
        logger.error(f"Missing required env vars: {', '.join(missing)}")
        sys.exit(1)

    return config


def _in_window() -> bool:
    hour = datetime.now(UK_TZ).hour
    return WINDOW_START <= hour < WINDOW_END


def _scheduled_job(config: dict) -> None:
    if not _in_window():
        logger.info(f"Outside active window (UK {datetime.now(UK_TZ).strftime('%H:%M')}) — skipping.")
        return
    from app.monitor import run_check
    run_check(config)


def run_app(port: int, interval_minutes: int) -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.web import app
    from app.db  import init_db

    init_db()
    config = _get_config(port)

    scheduler = BackgroundScheduler(timezone=UK_TZ)
    scheduler.add_job(
        lambda: _scheduled_job(config),
        trigger="interval",
        minutes=interval_minutes,
        id="westway_check",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — every {interval_minutes} min, active 09:00–00:00 UK time.")

    # Run once immediately if within window
    if _in_window():
        logger.info("Within active window — running initial check.")
        from app.monitor import run_check
        run_check(config)

    logger.info(f"Web app starting on http://0.0.0.0:{port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()


def check_now(port: int) -> None:
    from app.db      import init_db
    from app.monitor import run_check
    init_db()
    run_check(_get_config(port))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Westway Tennis Court Monitor")
    parser.add_argument("--port",      type=int, default=5000,  help="Web server port (default: 5000)")
    parser.add_argument("--interval",  type=int, default=30,    help="Check interval in minutes (default: 30)")
    parser.add_argument("--check-now", action="store_true",     help="Run one check immediately and exit")
    args = parser.parse_args()

    if args.check_now:
        check_now(args.port)
    else:
        run_app(args.port, args.interval)
