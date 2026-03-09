"""
Email notifier — sends an alert when Westway indoor tennis slots are available.
Uses Gmail SMTP with an App Password (no OAuth required).
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def _build_html(slots: list[dict]) -> str:
    rows = ""
    for s in slots:
        rows += (
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #ddd'>{s['date']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{s['time']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{s['court']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>"
            f"<a href='{s['url']}' style='color:#0066cc'>Book now</a></td>"
            f"</tr>"
        )

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
    <h2 style="color:#006633">🎾 Westway Indoor Tennis — Slots Available!</h2>
    <p>The following court slots are open for booking:</p>
    <table style="border-collapse:collapse;width:100%;max-width:700px">
      <thead>
        <tr style="background:#006633;color:#fff">
          <th style="padding:10px;text-align:left">Date</th>
          <th style="padding:10px;text-align:left">Time</th>
          <th style="padding:10px;text-align:left">Court</th>
          <th style="padding:10px;text-align:left">Action</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:20px;font-size:12px;color:#888">
      Sent by Westway Tennis Monitor at {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </p>
    </body></html>
    """


def _build_plain(slots: list[dict]) -> str:
    lines = ["Westway Indoor Tennis — Available Slots\n", "=" * 45]
    for s in slots:
        lines.append(f"  {s['date']}  |  {s['time']}  |  {s['court']}")
        lines.append(f"  Book: {s['url']}")
        lines.append("")
    lines.append(f"Sent at {datetime.now().strftime('%d/%m/%Y %H:%M')}")
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
    Send an email listing available court slots.
    Returns True on success, False on failure.
    """
    if not slots:
        return False

    subject = f"🎾 {len(slots)} Westway Tennis Slot(s) Available — Book Now!"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = to_address

    msg.attach(MIMEText(_build_plain(slots), "plain"))
    msg.attach(MIMEText(_build_html(slots),  "html"))

    # Google App Passwords may be written with dashes/spaces for readability
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
