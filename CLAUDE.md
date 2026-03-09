# Westway Tennis Booking — Claude Code Guide

## Project Overview
Automated monitor that scrapes the EveryoneActive booking system for available
indoor tennis court slots at Westway Sports & Fitness Centre (London) within
the next 7 days, then sends an email alert when slots are found.

## Repository
- GitHub: https://github.com/Raymondli073/Westway_Tennis_Booking
- Default branch: `main`

## Workflow
- Always use git feature branches for new features
- Commit with descriptive messages following conventional commits style
- Push to GitHub and open PRs for review before merging to `main`
- **Always update this CLAUDE.md file to reflect the latest project state whenever making git commits.**

## Stack
- **Scraping:** Playwright (Chromium, headless)
- **Scheduling:** APScheduler (BlockingScheduler)
- **Email:** Python smtplib + Gmail SMTP + App Password
- **Config:** python-dotenv (.env file)
- **Python:** 3.8+

## Environment
- Virtual environment: `.venv/` — activate with `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Install browser: `playwright install chromium`
- Configure: copy `.env.example` → `.env` and fill in credentials
- Run once: `python main.py`
- Run on schedule (every 30 min): `python main.py --schedule`
- Run on custom interval: `python main.py --schedule --interval 15`

## Project Structure
```
main.py                  # Entry point — CLI, scheduler setup
app/
├── __init__.py
├── scraper.py           # Playwright scraper — logs in, checks slots per day
├── notifier.py          # Gmail SMTP email alert builder + sender
└── monitor.py           # Orchestrator — deduplicates alerts via .seen_slots.json
.env.example             # Template for credentials (never commit .env)
requirements.txt         # Python dependencies
.seen_slots.json         # Runtime cache (auto-created, gitignored)
```

## Key Conventions
- Credentials via `.env` only — never committed to git
- `.seen_slots.json` tracks already-alerted slots to prevent duplicate emails
- `HEADLESS=false` in `.env` to watch the browser during debugging
- Gmail SMTP requires a 16-char App Password (not your normal Gmail password)
  → Google Account → Security → 2-Step Verification → App Passwords

## Slot Data Fields
Each slot dict: `{date, time, activity, courts_note, url}`
- `activity`: "Indoor Tennis (50 Mins)" or "Indoor Tennis Early Bird"
- `courts_note`: fixed string — court numbers are only assigned at checkout, not shown in the grid
- Slots are deduplicated by (date, time) before emailing — overlapping slots from different activities are merged
- Slots are sorted chronologically (date then time) before emailing
- Email subject and count reflect distinct slots only

## Booking System Navigation (Discovered via Playwright inspection)
- Login: `mrmLogin.aspx?siteId=0162` — fields: `#ctl00_MainContent_InputLogin`, `#ctl00_MainContent_InputPassword`
- Activity group: `input[value='Tennis Courts']` → ActivityID=162TENNIS
- Indoor activities: `Indoor Tennis (50 Mins)`, `Indoor Tennis Early Bird`
- Slot grid: `mrmResourceStatus.aspx` — each slot button has `data-qa-id` with date/time/availability
- Available slots: buttons without `disabled="disabled"` attribute
- Week navigation: `#ctl00_MainContent_dateForward1` button

## Gmail App Password Note
- Google App Passwords may be written with dashes (e.g. `xxxx-xxxx-xxxx-xxxx`) for readability
- The notifier strips dashes/spaces automatically before authenticating

## Required .env Variables
| Variable        | Description                                      |
|-----------------|--------------------------------------------------|
| EA_EMAIL        | EveryoneActive login email                       |
| EA_PASSWORD     | EveryoneActive login password                    |
| NOTIFY_EMAIL    | Recipient email (default: Raymondli073@gmail.com)|
| SMTP_USER       | Gmail address used to send alerts                |
| SMTP_PASSWORD   | Gmail App Password (16 chars)                    |
| DAYS_AHEAD      | Days to check ahead (default: 7)                 |
| HEADLESS        | true/false — hide/show browser (default: true)   |
