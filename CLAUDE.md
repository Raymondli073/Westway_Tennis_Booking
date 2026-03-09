# Westway Tennis Booking — Claude Code Guide

## Project Overview
Tennis court slot booking system for Westway Sports Centre. Built with Python/Flask, SQLite (dev) / PostgreSQL (prod).

## Repository
- GitHub: https://github.com/Raymondli073/Westway_Tennis_Booking
- Default branch: `main`

## Workflow
- Always use git feature branches for new features
- Commit with descriptive messages following conventional commits style
- Push to GitHub and open PRs for review before merging to `main`

## Stack
- **Backend:** Python / Flask
- **Database:** SQLite (dev), PostgreSQL (prod)
- **Frontend:** HTML / CSS / JavaScript (Jinja2 templates)
- **Auth:** Flask-Login

## Environment
- Python virtual environment: `.venv/`
- Run dev server: `flask run`
- Run tests: `pytest`
- Dependencies: `requirements.txt`

## Project Structure
```
app/
├── __init__.py       # App factory
├── models.py         # SQLAlchemy models
├── routes/           # Blueprint route handlers
│   ├── auth.py
│   ├── bookings.py
│   └── admin.py
├── templates/        # Jinja2 HTML templates
└── static/           # CSS, JS, images
tests/                # pytest test suite
```

## Key Conventions
- Use Flask blueprints for route organisation
- SQLAlchemy ORM for all database access
- Environment variables via `.env` (never commit secrets)
- `flask db migrate` / `flask db upgrade` for schema changes (Flask-Migrate)
