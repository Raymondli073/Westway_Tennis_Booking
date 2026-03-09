"""
Westway indoor tennis court availability scraper.

Flow:
  Login → Make a Booking → Tennis Courts
        → Indoor Tennis (50 Mins)       [ActivityID=162TENNIS]
        → Indoor Tennis Early Bird      [ActivityID=162TENN050OD002]
  Parse the weekly slot grid (Mon–Sun).
  Navigate forward one week if needed to cover `days_ahead` days.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout


LOGIN_URL     = "https://book.everyoneactive.com/Connect/mrmLogin.aspx?siteId=0162"
BOOKING_URL   = "https://book.everyoneactive.com/Connect/mrmResourceStatus.aspx"

INDOOR_ACTIVITIES = [
    "Indoor Tennis (50 Mins)",
    "Indoor Tennis Early Bird",
]


async def _login(page: Page, email: str, password: str) -> bool:
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
    await page.fill("#ctl00_MainContent_InputLogin",    email)
    await page.fill("#ctl00_MainContent_InputPassword", password)
    await page.click("#ctl00_MainContent_btnLogin")

    try:
        await page.wait_for_url(
            lambda url: "login" not in url.lower(),
            timeout=15000,
        )
        return True
    except PWTimeout:
        return "login" not in page.url.lower()


async def _navigate_to_activity(page: Page, activity_name: str) -> bool:
    """Navigate from home → Tennis Courts → specific activity."""
    try:
        await page.click("text=Make a Booking")
        await page.wait_for_load_state("networkidle", timeout=15000)

        await page.click("input[value='Tennis Courts']")
        await page.wait_for_load_state("networkidle", timeout=15000)

        await page.click(f"input[value='{activity_name}']")
        await page.wait_for_load_state("networkidle", timeout=15000)
        return True
    except Exception as e:
        print(f"[scraper] Navigation error for {activity_name!r}: {e}")
        return False


def _parse_grid(page_html: str, activity_name: str, booking_url: str) -> list[dict]:
    """
    Parse the slot grid from the page HTML.

    Each slot button has a data-qa-id like:
      button-ActivityID=162TENNIS Date=09/03/2026 06:00:00 Availability= Available
    Available slots do NOT have disabled="disabled".
    """
    slots = []

    # Find all slot buttons that are NOT disabled
    # Pattern: data-qa-id="button-ActivityID=... Date=DD/MM/YYYY HH:MM:SS Availability= <status>"
    pattern = re.compile(
        r'data-qa-id="button-ActivityID=\S+\s+Date=(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}):\d{2}\s+Availability=\s*([^"]+)"'
    )

    # Find buttons and whether they are disabled
    button_pattern = re.compile(
        r'<input[^>]*?(?P<disabled>disabled="disabled")?[^>]*?'
        r'data-qa-id="button-ActivityID=\S+\s+Date=(?P<date>\d{2}/\d{2}/\d{4})\s+'
        r'(?P<time>\d{2}:\d{2}):\d{2}\s+Availability=\s*(?P<avail>[^"]+)"',
        re.DOTALL,
    )

    for m in button_pattern.finditer(page_html):
        if m.group("disabled"):
            continue  # slot is not bookable
        avail = m.group("avail").strip()
        if "not available" in avail.lower() or "unavailable" in avail.lower():
            continue

        raw_date = m.group("date")          # DD/MM/YYYY
        raw_time = m.group("time")          # HH:MM
        try:
            dt = datetime.strptime(raw_date, "%d/%m/%Y")
            date_label = dt.strftime("%A %d %B %Y")
        except ValueError:
            date_label = raw_date

        slots.append({
            "date":        date_label,
            "time":        raw_time,
            "activity":    activity_name,
            "courts_note": "Available (court assigned at checkout)",
            "url":         booking_url,
        })

    return slots


async def _get_slots_for_activity(
    page: Page,
    activity_name: str,
    days_ahead: int,
) -> list[dict]:
    """Navigate to an activity and collect all available slots within days_ahead."""
    all_slots: list[dict] = []

    if not await _navigate_to_activity(page, activity_name):
        return all_slots

    today = datetime.today().date()
    cutoff = today + timedelta(days=days_ahead)

    # The grid shows one week at a time (Mon–Sun).
    # We may need to check the current week and possibly the next.
    weeks_checked = 0
    max_weeks = (days_ahead // 7) + 2  # safety limit

    while weeks_checked < max_weeks:
        html = await page.content()
        current_url = page.url
        week_slots = _parse_grid(html, activity_name, current_url)

        # Filter to slots within our date range
        for slot in week_slots:
            try:
                slot_date = datetime.strptime(slot["date"], "%A %d %B %Y").date()
                if today <= slot_date < cutoff:
                    all_slots.append(slot)
            except ValueError:
                all_slots.append(slot)  # include if we can't parse

        # Check if current week extends beyond our cutoff
        # (read the displayed date range from the page)
        date_range_el = await page.query_selector("#ctl00_MainContent_startDate")
        if date_range_el:
            range_text = await date_range_el.inner_text()  # e.g. "Mon 09 Mar to Sun 15 Mar"
        else:
            break

        # Extract the "to" date
        to_match = re.search(r"to\s+\w+\s+(\d+)\s+(\w+)", range_text)
        if to_match:
            try:
                year = datetime.today().year
                end_date = datetime.strptime(
                    f"{to_match.group(1)} {to_match.group(2)} {year}", "%d %b %Y"
                ).date()
                if end_date >= cutoff:
                    break  # covered enough days
            except ValueError:
                break

        # Navigate forward one week
        try:
            await page.click("#ctl00_MainContent_dateForward1")
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            break

        weeks_checked += 1

    return all_slots


async def get_available_slots(
    ea_email: str,
    ea_password: str,
    days_ahead: int = 7,
    headless: bool = True,
) -> list[dict]:
    """
    Returns a list of available indoor tennis slots at Westway for the
    next `days_ahead` days.  Each item: {date, time, court, url}.
    """
    all_slots: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        if not await _login(page, ea_email, ea_password):
            print("[scraper] Login failed — check credentials in .env")
            await browser.close()
            return all_slots

        print("[scraper] Logged in successfully.")

        for activity in INDOOR_ACTIVITIES:
            print(f"[scraper] Checking: {activity}")
            # Return to home between activities
            await page.goto(
                "https://book.everyoneactive.com/Connect/memberHomePage.aspx",
                wait_until="networkidle",
                timeout=20000,
            )
            slots = await _get_slots_for_activity(page, activity, days_ahead)
            print(f"[scraper]   → {len(slots)} available slot(s)")
            all_slots.extend(slots)

        await browser.close()

    return all_slots
