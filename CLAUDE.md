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
