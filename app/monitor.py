"""
Core monitor — ties together the scraper and notifier.
Sends alerts only when new consecutive blocks are found.
Emails all subscribers in the database with personalised unsubscribe links.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app.scraper  import get_available_slots
from app.notifier import send_alerts, _sort_and_dedup_slots, _find_consecutive_blocks
from app.db       import get_all_emails, init_db


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
    init_db()
    recipients = get_all_emails()

    if not recipients:
        print("[monitor] No subscribers — skipping check.")
        return 0

    ea_email    = config["EA_EMAIL"]
    ea_password = config["EA_PASSWORD"]
    smtp_user   = config["SMTP_USER"]
    smtp_pass   = config["SMTP_PASSWORD"]
    base_url    = config.get("BASE_URL", "http://localhost:5000")
    days_ahead  = int(config.get("DAYS_AHEAD", 7))
    headless    = config.get("HEADLESS", "true").lower() != "false"

    print(f"[monitor] Starting check ({len(recipients)} subscriber(s))…")

    raw_slots = asyncio.run(get_available_slots(ea_email, ea_password, days_ahead, headless))
    slots     = _sort_and_dedup_slots(raw_slots)
    highlight = _find_consecutive_blocks(slots)

    if not highlight:
        print("[monitor] No consecutive blocks — skipping email.")
        return 0

    seen = _load_seen()
    new_blocks: set[str] = set()
    for (date, _), label in highlight.items():
        key = _block_key(date, label)
        if key not in seen:
            new_blocks.add(key)

    if not new_blocks:
        print("[monitor] No NEW consecutive blocks — skipping email.")
        return 0

    print(f"[monitor] {len(new_blocks)} new block(s) — alerting {len(recipients)} subscriber(s).")
    sent = send_alerts(slots, recipients, smtp_user, smtp_pass, base_url)
    if sent > 0:
        seen.update(new_blocks)
        _save_seen(seen)

    return len(new_blocks)
