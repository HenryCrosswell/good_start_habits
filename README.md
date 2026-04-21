# good-start-habits

A personal dashboard that nags me into keeping my habits.

It runs in a browser (Flask), sits on a Raspberry Pi screen, and escalates visually the longer I ignore something — grey nudge, amber warning, flashing red. Habits are tracked with streaks. Fitness and budget data pull in from external APIs automatically.

---

## The build plan

### ✅ Phase 0 — Prototype (done)
The core habit logic already exists from a Streamlit prototype:
- Habit list, reminder times, and active hours defined in `config.py`
- Streak logic (increment, reset, daily maintenance) in `habits.py`
- Full test suite for all streak logic

---

### Phase 1 — Flask scaffold + SQLite migration
Swap Streamlit for Flask and move state from a JSON file to SQLite.

- Update `pyproject.toml`: remove Streamlit, add Flask, APScheduler, Plotly, python-dotenv
- Create `db.py` — SQLite connection and `habits` table
- Rewrite the storage layer in `habits.py` — same logic, SQLite instead of JSON
- Rewrite `app.py` as a Flask app with four stubbed routes: `/`, `/habits`, `/fitness`, `/budget`
- Create `templates/base.html` with shared layout and nav
- Update tests to mock the SQLite layer
- Delete `main.py` (dead code)

**Done when:** `flask run` works, all four routes respond, tests pass.

---

### Phase 2 — Standby clock + active hours
Make the clock the default view. During active hours it rotates automatically to habits.

- Build `templates/standby.html` — large clock and date, CSS only (vanilla JS just for the tick)
- Show a sleep message outside active hours
- During active hours: page auto-rotates to `/habits` on a timer, returns after 30 seconds
- Add `ROTATION_INTERVAL` to `config.py`

**Done when:** App opens to the clock, rotates to habits during the day, goes quiet at night.

---

### Phase 3 — Habits page with escalation colours
Full habits checklist. Colours shift the longer a habit is overdue.

- Build `templates/habits.html` — one button per habit, streak displayed
- `POST /habits/<name>/done` marks a habit complete
- Compute escalation level from time since the habit's reminder time:
  - 0–15 min → grey
  - 15–30 min → amber
  - 30–60 min → red
  - 60+ min → flashing red
- CSS classes drive the colour — no JS needed

**Done when:** Colours shift as time passes, completing a habit clears it, streaks survive restarts.

---

### Phase 4 — Strava integration (running)
Auto-complete "Run logged" when Strava sees an activity.

- Register a free Strava API app, store tokens in `.env`
- `integrations/strava.py`: `did_i_run_today() -> bool` and `get_recent_runs() -> list`
- Hook into the habits route — auto-tick if a run is detected
- Build `templates/fitness.html` with a Plotly graph (distance/pace over time)

**Done when:** Going for a run ticks the box without touching the app.

---

### Phase 5 — Hevy integration (weights)
Auto-complete "Workout logged" when Hevy sees a session.

- `integrations/hevy.py`: `did_i_lift_today() -> bool` and `get_recent_workouts() -> list`
- Hook into the habits route
- Extend the fitness page with volume and PR graphs

**Done when:** Logging a workout in Hevy ticks the box.

---

### Phase 6 — Budget page (TrueLayer)
Spending summary pulled from Monzo, Nationwide, and Amex.

- `integrations/truelayer.py` — OAuth for all three accounts, tokens stored in SQLite
- APScheduler refreshes tokens in the background
- `templates/budget.html` — spend by category, budget vs actual, transaction list (Plotly)

**Done when:** Budget page shows live data from all three accounts.
*(Build this last — it has the most OAuth complexity.)*

---

### Phase 7 — Raspberry Pi deployment
App runs headlessly on the Pi, launches on boot, displays in kiosk mode.

- Install all deps on Pi
- systemd service to start Flask on boot
- Chromium in kiosk mode pointing at `localhost:5000`

**Done when:** Pi boots straight into the dashboard, no keyboard needed.

---

## Running the app (Phase 1+)

```bash
uv sync
flask --app src/good_start_habits/app.py run
```

## Conventions

- Secrets go in `.env` — never hardcode, never commit
- `dashboard.db` and `.env` are gitignored
- Each integration returns a bool or a list — no UI logic inside integrations
- If an integration fails, log it and fall back to manual button — never crash the app
