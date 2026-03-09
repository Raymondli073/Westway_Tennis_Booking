"""
Westway indoor tennis court availability scraper.
Logs into EveryoneActive and checks for bookable slots in the next 7 days.
"""

import asyncio
import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout


CONNECT_BASE = "https://book.everyoneactive.com/Connect"
LOGIN_URL     = f"{CONNECT_BASE}/mrmLogin.aspx?siteId=0162"
SLOTS_URL     = f"{CONNECT_BASE}/mrmResourceStatus.aspx?siteId=0162"


async def _login(page: Page, email: str, password: str) -> bool:
    """Log into the EveryoneActive Connect booking system."""
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)

    # Fill credentials
    email_sel    = 'input[id*="email" i], input[name*="email" i], input[type="email"]'
    password_sel = 'input[id*="pass" i], input[name*="pass" i], input[type="password"]'
    submit_sel   = 'input[type="submit"], button[type="submit"], a:has-text("Login"), a:has-text("Sign in")'

    await page.fill(email_sel, email)
    await page.fill(password_sel, password)
    await page.click(submit_sel)

    try:
        # Wait until we're no longer on a login page
        await page.wait_for_function(
            "() => !window.location.href.toLowerCase().includes('login')",
            timeout=15000,
        )
        return True
    except PWTimeout:
        # Check if we're still on login (wrong creds) vs. navigated
        if "login" in page.url.lower():
            print("[scraper] Login failed — check credentials.")
            return False
        return True


async def _slots_for_date(page: Page, date: datetime.date) -> list[dict]:
    """Navigate to the slots page for a specific date and parse available courts."""
    url = f"{SLOTS_URL}&date={date.strftime('%Y-%m-%d')}&type=tennis"
    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except PWTimeout:
        print(f"[scraper] Timeout loading {url}")
        return []

    slots = []
    date_label = date.strftime("%A %d %B %Y")

    # ── Strategy 1: look for explicit availability cells / buttons ──────────
    available_els = await page.query_selector_all(
        "td.available, .slot-available, .activity-slot.available, "
        "[class*='available']:not([class*='un']):not([class*='not'])"
    )
    for el in available_els:
        text = (await el.inner_text()).strip()
        time_m = re.search(r"\b\d{1,2}[:.]\d{2}(?:\s*[ap]m)?\b", text, re.I)
        court_m = re.search(r"court\s*\d+|indoor|pitch\s*\d+", text, re.I)
        slots.append({
            "date":   date_label,
            "time":   time_m.group(0) if time_m else "See website",
            "court":  court_m.group(0) if court_m else "Indoor Tennis Court",
            "url":    page.url,
        })

    # ── Strategy 2: fallback — any visible "Book" links with a time nearby ──
    if not slots:
        book_links = await page.query_selector_all(
            "a:has-text('Book'), button:has-text('Book')"
        )
        for link in book_links:
            try:
                # Walk up the DOM to get the row/container text
                container_text = await link.evaluate(
                    "el => {"
                    "  let node = el.closest('tr') || el.closest('[class*=\"slot\"]') || el.parentElement;"
                    "  return node ? node.innerText : '';"
                    "}"
                )
            except Exception:
                container_text = ""

            # Skip non-tennis entries
            if container_text and re.search(r"tennis|court", container_text, re.I):
                time_m = re.search(r"\b\d{1,2}[:.]\d{2}(?:\s*[ap]m)?\b", container_text, re.I)
                slots.append({
                    "date":   date_label,
                    "time":   time_m.group(0) if time_m else "See website",
                    "court":  "Indoor Tennis Court",
                    "url":    page.url,
                })

    return slots


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
            await browser.close()
            return all_slots

        print("[scraper] Authenticated. Checking availability…")
        today = datetime.today().date()

        for i in range(days_ahead):
            target = today + timedelta(days=i)
            print(f"[scraper]  → {target.strftime('%a %d %b %Y')}", end="  ")
            day_slots = await _slots_for_date(page, target)
            print(f"{len(day_slots)} slot(s) found")
            all_slots.extend(day_slots)

        await browser.close()

    return all_slots
