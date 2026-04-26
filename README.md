# good-start-habits

A personal dashboard that shows me my habits, fitness data, and budget in one place. It runs in a browser (Flask), sits on a Raspberry Pi screen, and rotates passively between a clock and the habits page during active hours — no nagging, just a glance when the screen changes.

---

## What already exists (Phase 0 — prototype)

The core logic is complete and tested from a Streamlit prototype:

- `config.py` — habit list, active hours per day of week, reminder times per habit
- `habits.py` — streak logic: `day_diff`, `daily_maintenance`, `mark_done`, `check_current_datetime`
- Full test suite covering all streak scenarios

---

## Phase 1 — Flask scaffold + SQLite migration

**Goal:** Replace Streamlit with Flask. Move habit state from a JSON file into SQLite. All four page routes exist and respond. Tests still pass.

- [x] Step 1 — Simplify `config.py`
- [x] Step 2 — Implement `db.py`
- [x] Step 3 — Rewrite `habits.py` storage layer
- [x] Step 4 — Rewrite `app.py` as a Flask app
- [x] Step 5 — Create `templates/base.html`
- [x] Step 6 — Update tests
- [x] Step 7 — Delete `main.py`

### Step 1 — Simplify `config.py`

`HABIT_REMINDER_TIME` currently stores both which days a habit runs and what time to remind you. Since there's no time-based escalation, the times aren't needed. Replace it with `HABIT_ACTIVE_DAYS` — a dict mapping each habit to just a list of active days. This drives which habits show up today.

### Step 2 — Implement `db.py`

SQLite stores everything in a single file (`dashboard.db`). `db.py` provides two functions:

- **`get_db()`** — opens a connection to `dashboard.db` for the current request. Flask's `g` object (a request-scoped namespace) holds the connection so it's only opened once per request. A `teardown_appcontext` hook closes it automatically when the request ends.
- **`init_db()`** — runs `CREATE TABLE IF NOT EXISTS habits (...)` once at app startup. Safe to call every time — it only creates the table if it doesn't already exist.

The `habits` table has one row per habit, with four columns that map directly to what's currently in `state.json`:

| Column | Type | Meaning |
|---|---|---|
| `name` | TEXT PRIMARY KEY | Habit name. PRIMARY KEY enforces uniqueness. |
| `streak` | INTEGER NOT NULL DEFAULT 0 | Consecutive days completed. |
| `last_completed` | TEXT | Last completion date as `YYYY-MM-DD`. NULL if never done. SQLite has no date type — text is standard. |
| `done_today` | INTEGER NOT NULL DEFAULT 0 | 0 = not done, 1 = done. SQLite has no boolean type. |

### Step 3 — Rewrite `habits.py` storage layer

The streak logic (`day_diff`, `daily_maintenance`, `mark_done`, `check_current_datetime`) is correct and doesn't change. Only the I/O layer changes:

- **`state_init()`** — runs `INSERT OR IGNORE INTO habits (name) VALUES (?)` for each habit. INSERT OR IGNORE skips silently if the row already exists — the SQLite equivalent of "add if missing".
- **`load_state()`** — replaces the JSON file read with `SELECT name, streak, last_completed, done_today FROM habits`, building the same dict shape from the rows.
- **`mark_done()`** — instead of loading/saving the whole state, issues a targeted `UPDATE habits SET streak=?, done_today=1, last_completed=? WHERE name=?` for just the habit being marked.
- **`daily_maintenance()`** — reads all rows, computes what needs resetting, then issues UPDATE statements for affected habits.

Targeted SQL updates replace the load-everything/save-everything JSON pattern. SQL is designed for this; the old approach was a workaround for the flat-file format.

### Step 4 — Rewrite `app.py` as a Flask app

Flask maps URLs to Python functions via route decorators. A function decorated with `@app.route('/habits')` is called when someone visits `/habits`, and whatever it returns becomes the HTTP response.

`app.py` needs to:
1. Create the Flask app instance
2. Call `init_db()` at startup (before any requests)
3. Register the teardown hook from `db.py` to close connections after each request
4. Define four stubbed routes that return placeholder text: `/`, `/habits`, `/fitness`, `/budget`

The stubs don't touch the database yet — their only job is to confirm the app boots and routing works.

### Step 5 — Create `templates/base.html`

Jinja2 supports template inheritance. `base.html` is the shared skeleton: HTML boilerplate, a `<head>` with the stylesheet link, and a `<nav>` with links to all four pages. It defines a `{% block content %}{% endblock %}` region where child templates inject their content. A child template starts with `{% extends "base.html" %}` and fills in that block.

Also create `static/style.css` — minimal to start, just enough to confirm it's loading.

### Step 6 — Update tests

The current tests mock `load_state` and `save_state` to avoid touching `state.json`. After the migration the mocking targets change to the SQLite layer (`get_db()`). The test scenarios and assertions are identical — only the patch targets change.

### Step 7 — Delete `main.py`

Dead code. An infinite generator with no callers. Delete it.

**Phase 1 done when:** `flask run` starts cleanly, all four routes return 200, the nav renders, and `pytest` passes without touching the filesystem.

---

## Phase 2 — Standby clock + active hours

**Goal:** The app opens to a clock. During active hours it rotates to the habits page after `ROTATION_INTERVAL` seconds, stays there for `DWELL_TIME` seconds, then returns.

- [x] `templates/standby.html` — full-page clock and date. The time updates every second using `setInterval` in vanilla JS (the one JS exception in the project — everything else is server-rendered).
- [x] The `/` route calls `check_current_datetime()`. Outside active hours: show the clock with a quiet sleep message, no rotation. Inside active hours: pass `ROTATION_INTERVAL` to the template, which uses `setTimeout` to redirect to `/habits`.
- [x] The `/habits` route includes a `setTimeout` to redirect back to `/` after `DWELL_TIME` seconds. This creates the passive loop: clock → habits → clock → habits...
- [x] Add `ROTATION_INTERVAL` and `DWELL_TIME` to `config.py`.

**Phase 2 done when:** App opens to the clock, rotates to habits during active hours, goes quiet at night.

---

## Phase 3 — Habits page

**Goal:** Clean checklist of today's habits. Completing one persists across restarts. Streaks increment correctly.

- [x] `GET /habits` — checks today's day of week, filters `HABIT_ACTIVE_DAYS` to get today's habits, calls `daily_maintenance()`, queries SQLite for current state, passes a list of habit dicts to the template.
- [x] `POST /habits/<name>/done` — calls `mark_done()` for the named habit, then redirects back to `GET /habits`. The redirect (Post/Redirect/Get pattern) means refreshing the page won't resubmit the form.
- [x] `templates/habits.html` — extends `base.html`. Loops over today's habits and shows: name, streak count, and either a "Mark Done" form button or a done indicator depending on `done_today`.

**Why `daily_maintenance()` runs on page load:** The app may be off overnight. Calling it on the first habits page visit of the day catches up correctly without needing a background scheduler.

**Phase 3 done when:** Today's habits show up, completing one persists, streaks increment correctly, rotation from Phase 2 still works.

---

## Phase 4 — Strava integration (running)

**Goal:** "Run logged" auto-completes when Strava sees an activity. Fitness page shows running data.

- [ ] New file `strava.py` with `did_i_run_today() -> bool` and `get_recent_runs() -> list[dict]`. OAuth tokens stored in `.env`, refreshed via APScheduler.
- [ ] The habits route checks `did_i_run_today()` and auto-ticks "Run logged" if true.
- [ ] `templates/fitness.html` — Plotly graph of distance/pace over time.

**Phase 4 done when:** Going for a run ticks the box without touching the app.

---

## Phase 5 — Hevy integration (weights)

**Goal:** "Workout logged" auto-completes when Hevy sees a session. Fitness page extended with weights data.

- [ ] New file `hevy.py` with `did_i_lift_today() -> bool` and `get_recent_workouts() -> list[dict]`. API key in `.env`.
- [ ] Hook into habits route; extend `templates/fitness.html` with volume and PR graphs.

**Phase 5 done when:** Logging a workout in Hevy ticks the box.

---

## Phase 6 — Budget page (TrueLayer)

**Goal:** Spending summary across Monzo, Nationwide, and Amex.

**Before starting:** Verify that Amex and Nationwide are on TrueLayer's supported bank list — do not assume coverage. Build and test fully in TrueLayer sandbox mode before connecting real accounts.

- [ ] New file `truelayer.py`. OAuth for all three accounts; tokens stored in SQLite (not `.env` — they refresh too frequently).
- [ ] Token schema includes `expires_at`. Refresh logic checks expiry per-request; APScheduler is a backstop, not the primary mechanism.
- [ ] `templates/budget.html` — spend by category, budget vs actual (Plotly).

**Phase 6 done when:** Budget page shows live data from all three accounts.
*(Build this last — it has the most OAuth complexity.)*

---

## Phase 7 — Raspberry Pi deployment

**Goal:** App runs headlessly on the Pi, launches on boot, displays in kiosk mode.

- [ ] systemd service to start Flask on boot
- [ ] Chromium in kiosk mode pointing at `localhost:5000`
- [ ] No code changes — just deployment and hardware testing

**Phase 7 done when:** Pi boots straight into the dashboard, no keyboard needed.

---

## Running the app

```bash
uv sync
flask --app src/good_start_habits/app.py run
```

---

## Conventions

- Secrets go in `.env` — never hardcode, never commit
- `dashboard.db` and `.env` are gitignored
- Each integration returns a bool or a list — no UI logic inside integrations
- If an integration fails, log it and fall back to manual button — never crash the app
- All business logic in Python — keep Jinja templates thin
- No external CSS frameworks — plain CSS only
