"""
Email notifier — sends an alert when Westway indoor tennis slots are available.
Uses Gmail SMTP with an App Password (no OAuth required).
"""

from __future__ import annotations

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _sort_slots(slots: list[dict]) -> list[dict]:
    """Sort slots chronologically by date then time."""
    def sort_key(s: dict):
        try:
            return datetime.strptime(f"{s['date']} {s['time']}", "%A %d %B %Y %H:%M")
        except ValueError:
            return datetime.max
    return sorted(slots, key=sort_key)


def _build_html(slots: list[dict]) -> str:
    rows = ""
    prev_date = None
    for s in slots:
        # Shade alternate dates for readability
        bg = "#f9f9f9" if s["date"] == prev_date or prev_date is None else "#ffffff"
        if s["date"] != prev_date:
            bg = "#eef7ee" if prev_date is None else (
                "#f9f9f9" if rows.count("#eef7ee") % 2 == 0 else "#eef7ee"
            )
            prev_date = s["date"]

        rows += (
            f"<tr style='background:{bg}'>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'><strong>{s['date']}</strong></td>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'>{s['time']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{s['activity']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;white-space:nowrap'>{s['courts_note']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>"
            f"<a href='{s['url']}' style='color:#0066cc;font-weight:bold'>Book now</a></td>"
            f"</tr>"
        )

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;margin:20px">
    <h2 style="color:#006633">Westway Indoor Tennis — Slots Available</h2>
    <p style="color:#555">The following indoor court slots are open for booking, sorted by date and time:</p>
    <table style="border-collapse:collapse;width:100%;max-width:800px;font-size:14px">
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
    <p style="margin-top:16px;font-size:13px;color:#555">
      <strong>Note:</strong> Specific court numbers are assigned at checkout.
      Click <em>Book now</em> to see which courts are available and complete your booking.
    </p>
    <p style="margin-top:20px;font-size:11px;color:#aaa">
      Westway Tennis Monitor &mdash; {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </p>
    </body></html>
    """


def _build_plain(slots: list[dict]) -> str:
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
        lines.append(f"  {s['time']}  |  {s['activity']}  |  {s['courts_note']}")
    lines += [
        "",
        f"Book here: https://book.everyoneactive.com/Connect/memberHomePage.aspx",
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
    Returns True on success, False on failure.
    """
    if not slots:
        return False

    sorted_slots = _sort_slots(slots)
    subject = f"[Westway Tennis] {len(slots)} slot(s) available — Book Now!"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = to_address

    msg.attach(MIMEText(_build_plain(sorted_slots), "plain"))
    msg.attach(MIMEText(_build_html(sorted_slots),  "html"))

    # Google App Passwords may be formatted with dashes/spaces for readability
    smtp_password = smtp_password.replace("-", "").replace(" ", "")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_address, msg.as_string())
        print(f"[notifier] Alert sent to {to_address} ({len(slots)} slot(s))")
        return True
    except Exception as e:
        print(f"[notifier] Failed to send email: {e}")
        return False
