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
- Sort view (`?view=sort`) for batch categorisation of uncategorised transactions — AJAX, no page reload
- UNSORT button on each transaction row — moves transaction back to "Other" so it appears in the sort queue
- Transfer category — assigning Transfer excludes a transaction from all spend totals
- Edit overlay on chart view — reclassify transactions in place without page reload
- Docker + Gunicorn production setup
- Railway deployment with persistent volume for SQLite (`DB_PATH` env var)

### Planned
- Phase 4 — Strava integration: `did_i_run_today()`, `get_recent_runs()`, auto-tick "Track run"
- Phase 5 — Hevy integration: `did_i_lift_today()`, `get_recent_workouts()`, auto-tick "Track workout"
- Phase 7 — Raspberry Pi kiosk: systemd service, Chromium kiosk mode

---

## Key patterns

### SQLite connection (Flask `g` object)
`db.py:get_db()` stores the connection on Flask's `g` object. A new connection is created per request and closed automatically when the request ends. `init_db()` runs on every request via `@app.before_request` — it uses `CREATE TABLE IF NOT EXISTS` so this is a no-op after the first run.

The APScheduler token refresh job opens its own connection directly using `DB_PATH` from `db.py` because it runs outside of a request context.

### Database path (`DB_PATH`)
The SQLite file path is read from the `DB_PATH` environment variable, falling back to `"dashboard.db"` for local dev. In production on Railway, `DB_PATH=/data/dashboard.db` points to a persistent volume mounted at `/data`, so the database (and OAuth tokens) survive deploys. The constant lives in `db.py` and is imported by `app.py` for the scheduler job.

### Habit visibility vs habit existence
Habits are always stored in the database. Whether they appear on the `/habits` page is controlled by `HABIT_ACTIVE_DAYS` in `config.py` — the template filters by today's day name. Adding a new habit only requires two changes: add to `HABITS` and add to `HABIT_ACTIVE_DAYS`.

### Transaction categorisation (three-pass)
`budget.py:map_category()` assigns a category in priority order:
1. **`category_overrides` table** — substring match on the lowercased description. First matching override wins. If the stored category is `"Transfer"`, returns `None` (excluded from all totals).
2. **`CATEGORY_MAP`** (`config.py`) — matched against TrueLayer's `transaction_classification` field.
3. **`DESCRIPTION_PATTERNS`** (`config.py`) — case-insensitive substring scan of the description. First match wins.
4. Fall back to `"Other"`.
5. `None` result at any step = excluded from all totals (transfers, income, savings movements).

Overrides are loaded into `budget._overrides` on each request via `load_overrides()`.

### Reclassification AJAX API
`POST /budget/api/reclassify` accepts `{ "description": "...", "category": "..." }` and returns `{ "ok": true }`. Used by:
- **Sort view SAVE RULE button** — saves override and removes the row from the sort list without a page reload
- **Edit overlay SAVE button** — moves the transaction to the new category in the client-side data structure
- **UNSORT button** — reclassifies the transaction as `"Other"` and removes the row from the current view

The older form-POST `POST /budget/reclassify` still exists for fallback but is no longer used by the UI.

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

## Railway deployment notes

- Persistent volume mounted at `/data`, set `DB_PATH=/data/dashboard.db` in Railway Variables
- To verify after deploy: open the service shell and run `ls -la /data/` — `dashboard.db` should be present with a non-zero size
