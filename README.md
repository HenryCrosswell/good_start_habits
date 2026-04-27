# good-start-habits

A personal dashboard that lives in a browser tab (or a Raspberry Pi screen). It shows your habits, budget, and a standby clock. During active hours the screen cycles between the clock and your habit checklist — no notifications, no nagging, just a passive glance when the display changes.

Built with Flask, SQLite, and Plotly. No external CSS frameworks, no JavaScript build step.

---

## Quick start

```bash
# Install dependencies
uv sync

# Create your .env file (see Configuration below)
cp .env.example .env  # or create it manually

# Run
flask --app src/good_start_habits/app.py run
```

The app will be at `http://localhost:5000`. The database (`dashboard.db`) is created automatically on first run.

---

## Project structure

```
src/good_start_habits/
├── app.py          # Flask app and all route handlers
├── config.py       # Everything you'll want to change — habits, hours, budgets
├── habits.py       # Streak logic: daily maintenance, mark done, active hours check
├── db.py           # SQLite connection management and schema creation
├── budget.py       # Transaction categorisation and Plotly chart generation
├── truelayer.py    # TrueLayer OAuth client and banking data API wrapper
├── templates/
│   ├── base.html   # Shared HTML skeleton, fonts, CSS variables
│   ├── clock.html  # Standby page with animated clock
│   ├── habits.html # Daily habit checklist with streaks
│   ├── budget.html # Budget dashboard with charts
│   └── debug.html  # Page transition tester (dev only)
└── static/
    ├── style.css
    ├── transitions.css  # Keyframe animations for page transitions
    └── transitions.js   # Navigation system with randomised transition effects
tests/
├── test_db.py
├── test_habits.py
├── test_budget.py
└── test_truelayer.py
```

---

## Configuration

Almost everything you'd want to change lives in `config.py` and `.env`.

### `.env` — secrets and environment flags

```
SECRET_KEY=<any long random string>        # Flask session signing key
TRUELAYER_CLIENT_ID=<from TrueLayer app>
TRUELAYER_CLIENT_SECRET=<from TrueLayer app>
TRUELAYER_REDIRECT_URI=http://localhost:5000/auth/callback
TRUELAYER_SANDBOX=true                     # Set to false to use real bank connections
```

`SECRET_KEY` is required even if you're not using the budget features. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.

`TRUELAYER_SANDBOX=true` keeps you in TrueLayer's test environment with fake data. Flip to `false` and update the credentials only when you're ready for real bank connections.

---

### `config.py` — the main control panel

#### Habits

**`HABITS`** — the list of habit names tracked by the app. Add, remove, or rename entries here. Each name must also appear in `HABIT_ACTIVE_DAYS`.

**`HABIT_ACTIVE_DAYS`** — controls which days each habit appears. A habit won't show up on days it's not listed, so you can schedule habits to specific days of the week.

```python
# Example: make "Piano practice" weekdays only
"Piano practice": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
```

#### Active hours

**`ACTIVE_TIMES`** — the window each day when the dashboard is "live". Outside this window the clock shows a quiet message and the habit page rotation stops. Times are 24-hour `HH:MM:SS` strings.

```python
ACTIVE_TIMES = {
    "Monday": ("06:00:00", "21:00:00"),
    ...
    "Saturday": ("08:00:00", "21:00:00"),
}
```

#### Clock rotation

**`ROTATION_INTERVAL`** — seconds before the clock auto-navigates to the habits page (when active). Currently randomised between 5 and 15 on each app start. Replace `randint(5, 15)` with a fixed value like `1800` (30 min) once you've decided on an interval.

**`DWELL_TIME`** — seconds the habits page stays visible before returning to the clock. Same deal — randomised now, fix it when you're happy.

#### Budget limits

**`BUDGET_LIMITS`** — your monthly spending limits per category, in pounds. This is what the budget page compares actual spend against.

```python
BUDGET_LIMITS = {
    "Groceries": 200.0,
    "Food & Coffee": 80.0,
    "Eating Out & Social": 120.0,
    "Transport": 480.0,
    ...
}
```

**`PROVIDER_BUDGET_LIMITS`** — per-bank category caps. Useful when a category is split across accounts (e.g. train tickets on Amex, parking on Nationwide). When you filter the budget page to a specific bank, these limits apply instead of the global ones.

#### Transaction categorisation

**`CATEGORY_MAP`** — maps TrueLayer's transaction classifications (their taxonomy) to your personal categories. Keys with a `|` match both the top-level and sub-level classification; plain keys match top-level only. A value of `None` excludes the transaction from all spending totals (used for transfers and income).

**`DESCRIPTION_PATTERNS`** — fallback list for transactions TrueLayer can't classify, or where the classification isn't specific enough. Matched case-insensitively as substrings, first match wins. Add new entries here when you spot a recurring merchant landing in the wrong category.

```python
DESCRIPTION_PATTERNS = [
    ("tesco", "Food & Coffee"),
    ("zizzi", "Eating Out & Social"),
    ("trainline", "Transport"),
    ("transfer to", None),  # None = exclude entirely
    ...
]
```

---

## Pages and routes

| Route | Method | What it does |
|---|---|---|
| `/` | GET | Standby clock. Rotates to `/habits` during active hours. |
| `/habits` | GET | Today's habit checklist. Calls `daily_maintenance()` on load. |
| `/habits/<name>/done` | POST | Marks a habit done, increments streak. Redirects back. |
| `/habits/<name>/undo` | POST | Undoes a same-day completion. Redirects back. |
| `/budget` | GET | Budget dashboard. Accepts `?view=month\|year`, `?projection=1`, `?provider=monzo\|...` |
| `/auth/connect/<provider>` | GET | Starts TrueLayer OAuth for `monzo`, `nationwide`, or `amex`. |
| `/auth/callback` | GET | OAuth callback — exchanges code for tokens, saves to SQLite. |
| `/auth/disconnect/<provider>` | POST | Removes stored tokens for a provider. |
| `/debug` | GET | Page transition tester. |

---

## How habits work

When you visit `/habits`, `daily_maintenance()` runs first. It checks when each habit was last completed and applies these rules:

- **Same day** — no change.
- **1 day ago** — resets `done_today` so the button is available again.
- **2 days ago** — resets `done_today`, logs a warning. Streak is preserved (one missed day doesn't break it).
- **3+ days ago** — resets both `done_today` and `streak` to zero.

Clicking "DONE" increments the streak and records today's date. Clicking "UNDO" on the same day reverses it. Streaks are stored in SQLite so they survive restarts.

---

## How the budget works

The budget page fetches the last 30 days of transactions from any connected bank accounts (TrueLayer Data API), then categorises each transaction using the logic in `budget.py`:

1. Check `CATEGORY_MAP` for a match on TrueLayer's `transaction_classification` field.
2. If no match, scan `DESCRIPTION_PATTERNS` for a substring match on the transaction description.
3. Fall back to `"Other"`.
4. If the result is `None` (transfer, income, internal payment) — exclude from totals.

Charts are built with Plotly and rendered in the browser. The primary view is a burn-rate line graph — one line per category, x-axis is days of the month, y-axis is cumulative spend. A dotted horizontal line marks the budget limit. Toggle projection on to see a linear extrapolation to month-end.

OAuth tokens are stored in SQLite (not `.env`) because they refresh frequently. An APScheduler background job refreshes tokens hourly. Tokens are also checked and refreshed on-demand before each API call.

---

## Database

SQLite, stored in `dashboard.db` in the working directory. Created automatically — you never need to run migrations manually.

| Table | Purpose |
|---|---|
| `habits` | One row per habit: name, streak, last_completed date, done_today flag |
| `tl_tokens` | OAuth access/refresh tokens per provider, with expiry timestamp |
| `oauth_state` | Single-use PKCE + CSRF state tokens during OAuth flow (10-minute TTL) |

---

## Running tests

```bash
pytest
```

Tests use in-memory SQLite — they don't touch `dashboard.db` or make network calls. The test suite covers streak logic, database initialisation, transaction categorisation, and TrueLayer OAuth helpers.

```bash
pytest -v              # verbose output
pytest tests/test_budget.py   # single file
pytest --cov=src       # with coverage
```

---

## Linting and formatting

```bash
ruff check .           # lint
ruff format .          # format
mypy src/              # type check
```

---

## Adding a new habit

1. Add the name to `HABITS` in `config.py`.
2. Add it to `HABIT_ACTIVE_DAYS` with the days you want it to appear.
3. Restart the app — `db.py` uses `INSERT OR IGNORE`, so the new row is added automatically without touching existing data.

## Adding a new spending category

1. Add it to `BUDGET_LIMITS` in `config.py` with a monthly limit.
2. Add classification mappings to `CATEGORY_MAP` (if TrueLayer's taxonomy covers it).
3. Add description patterns to `DESCRIPTION_PATTERNS` for merchants that won't match by classification.
4. Optionally add per-provider limits to `PROVIDER_BUDGET_LIMITS`.

---

## What's built and what's next

| Phase | Status | What |
|---|---|---|
| Flask scaffold + SQLite | Done | Routes, DB, habit storage |
| Standby clock + active hours | Done | Clock page, passive rotation |
| Habits page | Done | Checklist, streaks, undo |
| Budget page (TrueLayer) | Mostly done | OAuth, charts, categorisation — UI refinement ongoing |
| Strava integration | Planned | Auto-tick "Track run" when a run is logged |
| Hevy integration | Planned | Auto-tick "Track workout" when a session is logged |
| Raspberry Pi deployment | Planned | systemd service, Chromium kiosk mode |

---

## Conventions

- Credentials go in `.env` — never hardcoded, never committed.
- `dashboard.db` and `.env` are gitignored.
- Each integration returns a bool or a list — no UI logic inside integrations.
- If an integration fails, log it and fall back to the manual button — never crash the app.
- Business logic lives in Python — Jinja templates stay thin.
- No external CSS frameworks — plain CSS only.
