"""
Email notifier — sends alerts when Westway indoor tennis slots are available.
Uses Gmail SMTP with an App Password (no OAuth required).
Supports multiple recipients, each with a personalised unsubscribe link.
"""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _sort_and_dedup_slots(slots: list[dict]) -> list[dict]:
    """Deduplicate by (date, time), keeping first occurrence, then sort chronologically."""
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
    Returns {(date, time): range_label} for every slot in a qualifying block.
    e.g. {("Thursday 12 March 2026", "15:00"): "15:00–18:00", ...}
    """
    parsed = []
    for s in slots:
        try:
            dt = datetime.strptime(f"{s['date']} {s['time']}", "%A %d %B %Y %H:%M")
            parsed.append((dt, s["date"]))
        except ValueError:
            pass

    by_date: dict[str, list[datetime]] = {}
    for dt, date_str in parsed:
        by_date.setdefault(date_str, []).append(dt)

    highlight: dict[tuple, str] = {}
    for date_str, times in by_date.items():
        times.sort()
        i = 0
        while i < len(times):
            run = [times[i]]
            j = i + 1
            while j < len(times) and times[j] - times[j - 1] == timedelta(hours=1):
                run.append(times[j])
                j += 1
            if len(run) >= 2:
                label = f"{run[0].strftime('%H:%M')}–{(run[-1] + timedelta(hours=1)).strftime('%H:%M')}"
                for t in run:
                    highlight[(date_str, t.strftime("%H:%M"))] = label
            i = j if j > i else i + 1

    return highlight


def _consecutive_subject_parts(highlight: dict[tuple, str]) -> list[str]:
    """Concise subject-line strings for each distinct consecutive block."""
    seen: set[tuple] = set()
    parts = []
    for (date_str, _), label in highlight.items():
        key = (date_str, label)
        if key not in seen:
            seen.add(key)
            try:
                short = datetime.strptime(date_str, "%A %d %B %Y").strftime("%a %d %b")
            except ValueError:
                short = date_str
            parts.append(f"{short} {label}")
    return parts


def _build_html(slots: list[dict], highlight: dict[tuple, str], unsubscribe_url: str) -> str:
    HI_BG  = "#fff3cd"
    HI_BDR = "#ffc107"
    rows = ""
    date_color_map: dict[str, str] = {}
    color_cycle = ["#f0f7f0", "#ffffff"]
    color_idx = 0
    prev_date = None

    for s in slots:
        if s["date"] not in date_color_map:
            date_color_map[s["date"]] = color_cycle[color_idx % 2]
            color_idx += 1

        key        = (s["date"], s["time"])
        is_consec  = key in highlight
        bg         = HI_BG if is_consec else date_color_map[s["date"]]
        border     = f"border-left:4px solid {HI_BDR};" if is_consec else ""
        badge      = (f"<span style='background:{HI_BDR};color:#333;font-size:11px;"
                      f"padding:1px 5px;border-radius:3px;margin-left:6px;font-weight:bold'>"
                      f"⏱ {highlight[key]}</span>") if is_consec else ""

        date_cell = (f"<strong>{s['date']}</strong>{badge}"
                     if s["date"] != prev_date or is_consec else "")
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
        f"<span style='background:{HI_BG};border-left:4px solid {HI_BDR};padding:2px 8px;'>"
        f"Highlighted rows</span> are part of a consecutive 2+ hour block.</p>"
    ) if highlight else ""

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
    <p style="margin-top:24px;font-size:11px;color:#aaa;border-top:1px solid #eee;padding-top:12px">
      Westway Tennis Monitor &mdash; {datetime.now().strftime("%d/%m/%Y %H:%M")}<br>
      <a href="{unsubscribe_url}" style="color:#aaa">Unsubscribe</a>
    </p>
    </body></html>
    """


def _build_plain(slots: list[dict], highlight: dict[tuple, str], unsubscribe_url: str) -> str:
    lines = ["Westway Indoor Tennis — Available Slots", "=" * 50, ""]
    prev_date = None
    for s in slots:
        if s["date"] != prev_date:
            lines.append(f"\n{s['date']}")
            lines.append("-" * len(s["date"]))
            prev_date = s["date"]
        key = (s["date"], s["time"])
        tag = f"  [consecutive: {highlight[key]}]" if key in highlight else ""
        lines.append(f"  {s['time']}  |  {s['activity']}{tag}")
    lines += [
        "",
        "Book here: https://book.everyoneactive.com/Connect/memberHomePage.aspx",
        "",
        f"Sent at {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Unsubscribe: {unsubscribe_url}",
    ]
    return "\n".join(lines)


def send_alerts(
    slots: list[dict],
    recipients: list[str],
    smtp_user: str,
    smtp_password: str,
    base_url: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> int:
    """
    Send individual alert emails to each recipient with a personalised unsubscribe link.
    Returns the number of emails successfully sent.
    """
    if not slots or not recipients:
        return 0

    from app.db import get_token

    sorted_slots = _sort_and_dedup_slots(slots)
    highlight    = _find_consecutive_blocks(sorted_slots)
    consec_parts = _consecutive_subject_parts(highlight)

    base_subject = f"[Westway Tennis] {len(sorted_slots)} slot(s) available"
    consec_str   = "; ".join(consec_parts)
    subject      = f"{base_subject} — incl. {consec_str}" if consec_parts else f"{base_subject} — Book Now!"

    smtp_password = smtp_password.replace("-", "").replace(" ", "")
    sent_count = 0

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)

            for to_address in recipients:
                token         = get_token(to_address)
                unsub_url     = f"{base_url}/unsubscribe?token={token}"
                plain         = _build_plain(sorted_slots, highlight, unsub_url)
                html          = _build_html(sorted_slots, highlight, unsub_url)

                msg            = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"]    = smtp_user
                msg["To"]      = to_address
                msg.attach(MIMEText(plain, "plain"))
                msg.attach(MIMEText(html,  "html"))

                try:
                    server.sendmail(smtp_user, to_address, msg.as_string())
                    sent_count += 1
                    print(f"[notifier]   ✓ {to_address}")
                except Exception as e:
                    print(f"[notifier]   ✗ {to_address}: {e}")

    except Exception as e:
        print(f"[notifier] SMTP error: {e}")
        return sent_count

    print(f"[notifier] Sent {sent_count}/{len(recipients)} alert(s) — {subject}")
    return sent_count


# Backwards-compatible single-recipient wrapper used in tests / manual runs
def send_alert(
    slots: list[dict],
    to_address: str,
    smtp_user: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> bool:
    sent = send_alerts(
        slots,
        recipients=[to_address],
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        base_url="http://localhost:5000",
        smtp_host=smtp_host,
        smtp_port=smtp_port,
    )
    return sent > 0
