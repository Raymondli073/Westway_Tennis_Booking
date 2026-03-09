"""
Email notifier — sends an alert when Westway indoor tennis slots are available.
Uses Gmail SMTP with an App Password (no OAuth required).
"""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _sort_and_dedup_slots(slots: list[dict]) -> list[dict]:
    """Deduplicate by (date, time), keeping the first occurrence, then sort chronologically."""
    seen: set[tuple] = set()
    unique = []
    for s in slots:
        key = (s["date"], s["time"])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    def sort_key(s: dict):
        try:
            return datetime.strptime(f"{s['date']} {s['time']}", "%A %d %B %Y %H:%M")
        except ValueError:
            return datetime.max

    return sorted(unique, key=sort_key)


def _find_consecutive_blocks(slots: list[dict]) -> dict[tuple, str]:
    """
    Find groups of 2+ consecutive hourly slots on the same date.

    Returns a dict mapping (date, time) -> range_label for every slot
    that belongs to a consecutive block of >= 2 slots.
    e.g. {("Thursday 12 March 2026", "15:00"): "15:00-18:00", ...}
    """
    # Parse each slot into a datetime
    parsed = []
    for s in slots:
        try:
            dt = datetime.strptime(f"{s['date']} {s['time']}", "%A %d %B %Y %H:%M")
            parsed.append((dt, s["date"], s["time"]))
        except ValueError:
            pass

    # Group by date
    by_date: dict[str, list[datetime]] = {}
    for dt, date_str, _ in parsed:
        by_date.setdefault(date_str, []).append(dt)

    highlight: dict[tuple, str] = {}

    for date_str, times in by_date.items():
        times.sort()
        # Walk through times, building consecutive runs (exactly 1 hour apart)
        i = 0
        while i < len(times):
            run = [times[i]]
            j = i + 1
            while j < len(times) and times[j] - times[j - 1] == timedelta(hours=1):
                run.append(times[j])
                j += 1

            if len(run) >= 2:
                start_str = run[0].strftime("%H:%M")
                end_str   = (run[-1] + timedelta(hours=1)).strftime("%H:%M")
                range_label = f"{start_str}–{end_str}"
                for t in run:
                    highlight[(date_str, t.strftime("%H:%M"))] = range_label

            i = j if j > i else i + 1

    return highlight


def _consecutive_subject_parts(highlight: dict[tuple, str]) -> list[str]:
    """Build concise subject-line strings for each distinct consecutive block."""
    # Collect unique (date, range_label) pairs in order
    seen: set[tuple] = set()
    parts = []
    for (date_str, _), range_label in highlight.items():
        key = (date_str, range_label)
        if key not in seen:
            seen.add(key)
            # Shorten date: "Thursday 12 March 2026" -> "Thu 12 Mar"
            try:
                dt = datetime.strptime(date_str, "%A %d %B %Y")
                short = dt.strftime("%a %d %b")
            except ValueError:
                short = date_str
            parts.append(f"{short} {range_label}")
    return parts


def _build_html(slots: list[dict], highlight: dict[tuple, str]) -> str:
    HIGHLIGHT_BG = "#fff3cd"   # amber — consecutive block
    HIGHLIGHT_BORDER = "#ffc107"
    rows = ""
    prev_date = None
    date_color_map: dict[str, str] = {}
    color_cycle = ["#f0f7f0", "#ffffff"]
    color_idx = 0

    for s in slots:
        if s["date"] not in date_color_map:
            date_color_map[s["date"]] = color_cycle[color_idx % 2]
            color_idx += 1

        key = (s["date"], s["time"])
        is_consec = key in highlight

        if is_consec:
            bg     = HIGHLIGHT_BG
            border = f"border-left:4px solid {HIGHLIGHT_BORDER};"
            badge  = (f"<span style='background:{HIGHLIGHT_BORDER};color:#333;"
                      f"font-size:11px;padding:1px 5px;border-radius:3px;"
                      f"margin-left:6px;font-weight:bold'>"
                      f"⏱ {highlight[key]}</span>")
        else:
            bg     = date_color_map[s["date"]]
            border = ""
            badge  = ""

        date_cell = (
            f"<strong>{s['date']}</strong>{badge}"
            if s["date"] != prev_date or is_consec
            else ""
        )
        prev_date = s["date"]

        rows += (
            f"<tr style='background:{bg};{border}'>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'>{date_cell}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'><strong>{s['time']}</strong></td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{s['activity']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'>{s['courts_note']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>"
            f"<a href='{s['url']}' style='color:#0066cc;font-weight:bold'>Book now</a></td>"
            f"</tr>"
        )

    legend = (
        f"<p style='margin-top:12px;font-size:13px'>"
        f"<span style='background:{HIGHLIGHT_BG};border-left:4px solid {HIGHLIGHT_BORDER};"
        f"padding:2px 8px;'>Highlighted rows</span> are part of a consecutive 2+ hour block."
        f"</p>"
        if highlight else ""
    )

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;margin:20px">
    <h2 style="color:#006633">Westway Indoor Tennis — Slots Available</h2>
    <p style="color:#555">Indoor court slots open for booking, sorted by date and time:</p>
    <table style="border-collapse:collapse;width:100%;max-width:820px;font-size:14px">
      <thead>
        <tr style="background:#006633;color:#fff">
          <th style="padding:10px;text-align:left">Date</th>
          <th style="padding:10px;text-align:left">Time</th>
          <th style="padding:10px;text-align:left">Activity</th>
          <th style="padding:10px;text-align:left">Courts</th>
          <th style="padding:10px;text-align:left">Action</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    {legend}
    <p style="margin-top:16px;font-size:13px;color:#555">
      <strong>Note:</strong> Specific court numbers are assigned at checkout.
    </p>
    <p style="margin-top:20px;font-size:11px;color:#aaa">
      Westway Tennis Monitor &mdash; {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </p>
    </body></html>
    """


def _build_plain(slots: list[dict], highlight: dict[tuple, str]) -> str:
    lines = [
        "Westway Indoor Tennis — Available Slots",
        "=" * 50,
        "",
    ]
    prev_date = None
    for s in slots:
        if s["date"] != prev_date:
            lines.append(f"\n{s['date']}")
            lines.append("-" * len(s["date"]))
            prev_date = s["date"]
        key = (s["date"], s["time"])
        consec_tag = f"  [consecutive: {highlight[key]}]" if key in highlight else ""
        lines.append(f"  {s['time']}  |  {s['activity']}{consec_tag}")
    lines += [
        "",
        "Book here: https://book.everyoneactive.com/Connect/memberHomePage.aspx",
        "",
        f"Sent at {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]
    return "\n".join(lines)


def send_alert(
    slots: list[dict],
    to_address: str,
    smtp_user: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> bool:
    """
    Send an email listing available court slots sorted by date/time.
    Consecutive 2+ hour blocks are highlighted in the email and subject.
    Returns True on success, False on failure.
    """
    if not slots:
        return False

    sorted_slots = _sort_and_dedup_slots(slots)
    highlight    = _find_consecutive_blocks(sorted_slots)
    consec_parts = _consecutive_subject_parts(highlight)

    base_subject = f"[Westway Tennis] {len(sorted_slots)} slot(s) available"
    if consec_parts:
        consec_str = "; ".join(consec_parts)
        subject = f"{base_subject} — incl. {consec_str}"
    else:
        subject = f"{base_subject} — Book Now!"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = to_address

    msg.attach(MIMEText(_build_plain(sorted_slots, highlight), "plain"))
    msg.attach(MIMEText(_build_html(sorted_slots, highlight),  "html"))

    smtp_password = smtp_password.replace("-", "").replace(" ", "")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_address, msg.as_string())
        consec_note = f", consecutive: {consec_str}" if consec_parts else ""
        print(f"[notifier] Alert sent to {to_address} ({len(sorted_slots)} distinct slot(s){consec_note})")
        return True
    except Exception as e:
        print(f"[notifier] Failed to send email: {e}")
        return False
