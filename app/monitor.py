"""
Core monitor — ties together the scraper and notifier.
Tracks previously seen consecutive blocks to avoid duplicate alerts.
Only sends an email when at least one consecutive block (2+ hours) is detected.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app.scraper  import get_available_slots
from app.notifier import send_alert, _sort_and_dedup_slots, _find_consecutive_blocks


# Persists already-alerted consecutive blocks between runs
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


def _block_key(date: str, range_label: str) -> str:
    return f"{date}|{range_label}"


def run_check(config: dict) -> int:
    """
    Run one check cycle.
    Sends an alert only when new consecutive blocks (2+ hours) are found.
    Returns the number of NEW consecutive blocks alerted on.
    """
    ea_email    = config["EA_EMAIL"]
    ea_password = config["EA_PASSWORD"]
    to_email    = config["NOTIFY_EMAIL"]
    smtp_user   = config["SMTP_USER"]
    smtp_pass   = config["SMTP_PASSWORD"]
    days_ahead  = int(config.get("DAYS_AHEAD", 7))
    headless    = config.get("HEADLESS", "true").lower() != "false"

    print("[monitor] Starting availability check…")

    raw_slots   = asyncio.run(get_available_slots(ea_email, ea_password, days_ahead, headless))
    slots       = _sort_and_dedup_slots(raw_slots)
    highlight   = _find_consecutive_blocks(slots)

    if not highlight:
        print("[monitor] No consecutive blocks found — skipping email.")
        return 0

    # Find distinct consecutive blocks
    seen = _load_seen()
    new_blocks: set[str] = set()
    for (date, _), label in highlight.items():
        key = _block_key(date, label)
        if key not in seen:
            new_blocks.add(key)

    if not new_blocks:
        print("[monitor] No NEW consecutive blocks — skipping email.")
        return 0

    print(f"[monitor] {len(new_blocks)} new consecutive block(s) found — sending alert.")
    sent = send_alert(slots, to_email, smtp_user, smtp_pass)
    if sent:
        seen.update(new_blocks)
        _save_seen(seen)

    return len(new_blocks)
