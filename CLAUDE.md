# good-start-habits — CLAUDE.md

A personal dashboard for tracking habits, fitness, and budget. Built in Python/Flask, deployed on Railway (Docker) and optionally on a Raspberry Pi as a kiosk.

---

## Developer context

- Experienced Python developer, first time with Flask and SQLite
- Explain Flask and SQLite patterns rather than assuming familiarity
- Do not include code snippets in responses unless explicitly requested

---

## Stack

| Thing | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | |
| Web framework | Flask | Lightweight, Pi-friendly |
| Templating | Jinja2 | Bundled with Flask |
| Database | SQLite (`dashboard.db`) | Zero setup, local, Pi-friendly |
| Graphs | Plotly (Python) | Renders in browser, no heavy deps |
| Scheduling | APScheduler | Background token refresh |
| Production server | Gunicorn (1 worker, 4 threads) | Single worker keeps APScheduler simple |
| Styling | Plain CSS | No build step, no frameworks |

---

## Project structure

```
src/good_start_habits/
├── app.py          # Flask app and all route handlers
├── config.py       # Everything user-configurable — habits, hours, budgets
├── habits.py       # Streak logic: daily_maintenance, mark_done, check_current_datetime
├── db.py           # SQLite connection management and schema creation
├── budget.py       # Transaction categorisation and Plotly chart builders
└── truelayer.py    # TrueLayer OAuth client and banking data API wrapper
templates/
├── base.html       # Shared skeleton, fonts, CSS variables
├── clock.html      # Standby page with animated clock
├── habits.html     # Daily habit checklist with streaks
├── budget.html     # Budget dashboard with charts
└── debug.html      # Page transition tester (dev only)
static/
├── style.css
├── transitions.css # Keyframe animations for page transitions
└── transitions.js  # Navigation system with randomised transition effects
tests/
├── test_db.py
├── test_habits.py
├── test_budget.py
└── test_truelayer.py
```

---

## Current state

### Done
- Flask scaffold + SQLite migration from Streamlit prototype
- Standby clock with active hours per day of week
- Habits checklist with streak tracking, undo, per-day visibility
- Budget page: TrueLayer OAuth (Monzo, Nationwide, Amex), transaction categorisation, burn-rate line graphs, monthly/yearly views, projection, sinking fund tracking, savings baselines, wrong-card detection, inline reclassification
- Docker + Gunicorn production setup
- Railway deployment

### Planned
- Phase 4 — Strava integration: `did_i_run_today()`, `get_recent_runs()`, auto-tick "Track run"
- Phase 5 — Hevy integration: `did_i_lift_today()`, `get_recent_workouts()`, auto-tick "Track workout"
- Phase 7 — Raspberry Pi kiosk: systemd service, Chromium kiosk mode

---

## Key patterns

### SQLite connection (Flask `g` object)
`db.py:get_db()` stores the connection on Flask's `g` object. A new connection is created per request and closed automatically when the request ends. `init_db()` runs on every request via `@app.before_request` — it uses `CREATE TABLE IF NOT EXISTS` so this is a no-op after the first run.

The APScheduler token refresh job opens its own connection directly (`sqlite3.connect("dashboard.db")`) because it runs outside of a request context.

### Habit visibility vs habit existence
Habits are always stored in the database. Whether they appear on the `/habits` page is controlled by `HABIT_ACTIVE_DAYS` in `config.py` — the template filters by today's day name. Adding a new habit only requires two changes: add to `HABITS` and add to `HABIT_ACTIVE_DAYS`.

### Transaction categorisation (two-pass)
`budget.py:map_category()` runs two passes:
1. Check `CATEGORY_MAP` for a match on TrueLayer's `transaction_classification` field.
2. If no match, scan `DESCRIPTION_PATTERNS` for a case-insensitive substring match on the description. First match wins.
3. Fall back to `"Other"`.
4. `None` result = exclude from all totals (transfers, income, savings movements).

Per-session overrides are stored in the `category_overrides` SQLite table and loaded into `budget._overrides` on each request. The override check happens before the two-pass default logic.

### Sinking funds
Sinking fund categories (Haircut, Gigs, etc.) reset their cumulative spend on defined months (`SINKING_FUND_RESETS`). `budget.py:_sf_period_start()` finds the most recent reset month and `budget.py:earliest_sf_since()` widens the TrueLayer fetch window to include the reset point.

### APScheduler + Gunicorn
The scheduler guard in `app.py` uses `if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"`. In production (Gunicorn, debug=False) this evaluates to True and the scheduler starts. With `--workers 1` only one scheduler instance exists.

---

## Conventions

- Credentials go in `.env` — never hardcoded, never committed
- `dashboard.db` and `.env` are gitignored
- Each integration returns a bool or a list — no UI logic inside integrations
- If an integration fails, log it and fall back to the manual button — never crash the app
- Business logic lives in Python — Jinja templates stay thin
- No external CSS frameworks — plain CSS only
- No comments explaining what code does — only why when it's non-obvious

---

## Running the app

```bash
# Local dev
uv sync
flask --app src/good_start_habits/app.py run

# Docker (production, also works on Pi)
docker compose up -d
```
