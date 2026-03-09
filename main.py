"""
Westway Tennis Monitor — entry point.

Usage:
  python main.py              # run once immediately
  python main.py --schedule   # run on a schedule (default: every 30 min)
  python main.py --interval 15  # run every 15 minutes
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _get_config() -> dict:
    required = ["EA_EMAIL", "EA_PASSWORD", "SMTP_USER", "SMTP_PASSWORD"]
    config = {k: os.getenv(k, "") for k in required}
    config["NOTIFY_EMAIL"] = os.getenv("NOTIFY_EMAIL", "Raymondli073@gmail.com")
    config["DAYS_AHEAD"]   = os.getenv("DAYS_AHEAD", "7")
    config["HEADLESS"]     = os.getenv("HEADLESS", "true")

    missing = [k for k in required if not config[k]]
    if missing:
        print(f"[main] Missing required env vars: {', '.join(missing)}")
        print("       Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    return config


def run_once(config: dict) -> None:
    from app.monitor import run_check
    run_check(config)


def run_scheduled(config: dict, interval_minutes: int) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from app.monitor import run_check

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: run_check(config),
        trigger="interval",
        minutes=interval_minutes,
        id="westway_check",
    )

    print(f"[main] Scheduler started — checking every {interval_minutes} minute(s).")
    print("[main] Press Ctrl+C to stop.\n")

    # Run once immediately on startup
    run_check(config)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[main] Stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Westway Tennis Court Monitor")
    parser.add_argument(
        "--schedule", action="store_true",
        help="Keep running on a schedule instead of a single check",
    )
    parser.add_argument(
        "--interval", type=int, default=30, metavar="MINUTES",
        help="Check interval in minutes when using --schedule (default: 30)",
    )
    args = parser.parse_args()

    cfg = _get_config()

    if args.schedule:
        run_scheduled(cfg, args.interval)
    else:
        run_once(cfg)
