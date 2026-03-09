"""
Core monitor — ties together the scraper and notifier.
Tracks previously seen slots to avoid duplicate alerts.
"""

import asyncio
import json
import os
from pathlib import Path

from app.scraper  import get_available_slots
from app.notifier import send_alert


# File used to cache already-alerted slots (persist between runs)
SEEN_CACHE = Path(__file__).parent.parent / ".seen_slots.json"


def _load_seen() -> set[str]:
    if SEEN_CACHE.exists():
        try:
            return set(json.loads(SEEN_CACHE.read_text()))
        except Exception:
            pass
    return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_CACHE.write_text(json.dumps(sorted(seen)))


def _slot_key(slot: dict) -> str:
    return f"{slot['date']}|{slot['time']}|{slot['court']}"


def run_check(config: dict) -> int:
    """
    Run one check cycle.
    Returns the number of NEW slots found (and alerted on).
    """
    ea_email    = config["EA_EMAIL"]
    ea_password = config["EA_PASSWORD"]
    to_email    = config["NOTIFY_EMAIL"]
    smtp_user   = config["SMTP_USER"]
    smtp_pass   = config["SMTP_PASSWORD"]
    days_ahead  = int(config.get("DAYS_AHEAD", 7))
    headless    = config.get("HEADLESS", "true").lower() != "false"

    print("[monitor] Starting availability check…")

    slots = asyncio.run(
        get_available_slots(ea_email, ea_password, days_ahead, headless)
    )

    seen = _load_seen()
    new_slots = [s for s in slots if _slot_key(s) not in seen]

    if new_slots:
        print(f"[monitor] {len(new_slots)} new slot(s) found — sending alert.")
        sent = send_alert(new_slots, to_email, smtp_user, smtp_pass)
        if sent:
            seen.update(_slot_key(s) for s in new_slots)
            _save_seen(seen)
    else:
        print("[monitor] No new slots found.")

    return len(new_slots)
