# good-start-habits — CLAUDE.md

A personal dashboard for tracking habits, fitness, and budget.
Built in Python/Flask, runs in the browser now (WSL2), ports to Raspberry Pi later.

---

## Developer Context

- Experienced Python developer, first time using Flask and SQLite
- Explain Flask and SQLite patterns rather than assuming familiarity
- Do not include code snippets in responses unless explicitly requested

---

## Project Philosophy

- One problem at a time
- Working code at every phase — nothing half-built
- No external dependencies until they're genuinely needed
- Each phase builds directly on the last

---

## Stack

| Thing | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Only language needed |
| Web framework | Flask | Lightweight, Pi-friendly |
| Templating | Jinja2 | Bundled with Flask |
| Database | SQLite (`dashboard.db`) | Zero setup, local, Pi-friendly |
| Graphs | Plotly (Python) | Renders in browser, no heavy deps |
| Scheduling | APScheduler | Background jobs (token refresh etc.) |
| Styling | Plain CSS in Jinja templates | No build step, no frameworks |

---

## Project Structure (target)

```
src/good_start_habits/
├── __init__.py
├── app.py                  # Flask app, all routes
├── config.py               # Habits, active hours, active days per habit
├── habits.py               # Streak logic (SQLite-backed)
├── db.py                   # SQLite connection + schema
├── templates/
│   ├── base.html
│   ├── standby.html
│   ├── habits.html
│   ├── fitness.html
│   └── budget.html
├── static/
│   └── style.css
├── strava.py
├── hevy.py
└── truelayer.py
```

---

## Pages

| Page | Route | Notes |
|---|---|---|
| Standby (clock) | `/` | Default view. Large clock + date. Rotates to habits during active hours. |
| Habits | `/habits` | One button per habit, streak shown. Only shows habits relevant to today. |
| Fitness | `/fitness` | Running (Strava) + weights (Hevy) graphs via Plotly |
| Budget | `/budget` | Category budgets vs actual spend, burn-rate line graph, Monzo/Nationwide/Amex via TrueLayer |

---

## Habits (defined in config.py)

| Habit | When it appears | How it completes |
|---|---|---|
| SPF applied | Daily | Button |
| Vitamins & Omega-3 | Daily | Button |
| Log meal | Daily | Button |
| Piano practice | Daily | Button |
| Journal entry | Daily | Button |
| Neuroscience notes | Weekdays | Button |
| Check to-do book | Daily | Button |
| Workout logged | Mon / Wed / Fri | Button (Hevy API later) |
| Run logged | Tue / Thu / Sat | Button (Strava API later) |

Habit visibility is controlled by active days in `config.py` — habits not scheduled for today simply don't appear. There is no time-based urgency or escalation.

---

## Active Hours & Rotation

Active hours (defined per day in `config.py`) define the window when the dashboard is "live". Outside that window the clock shows with a quiet message — no habits, no data, just the time.

Within active hours the screen periodically transitions from the clock to the habits page, then back. The point is not to remind or nag — it's that a screen change draws the eye passively. You glance, you see your streaks and today's habits, you decide whether to act. Then the clock comes back.

Things still TBD / to explore:
- **Rotation interval:** fixed (e.g. every 20 min) or randomised within a range
- **Habits dwell time:** how long the habits page stays up before returning to the clock
- **Transition style:** randomly pick from a set of CSS transitions on each rotation (star wipe, rotate, scale, fade etc.) — the varied effect makes the change more eye-catching. Implement after basic rotation is working.

---

## Build Phases

### ✅ Already done (transfers from Streamlit prototype)
- Habit list defined in `config.py`
- Active hours per day of week in `config.py`
- Active days per habit in `config.py` (repurpose `HABIT_REMINDER_TIME` day schedule, drop times)
- Streak logic: `day_diff`, `daily_maintenance`, `mark_done`, `check_current_datetime` in `habits.py`
- Test suite covering all habit logic functions

---

### ✅ Phase 1 — Flask scaffold + SQLite migration
**Goal:** Replace Streamlit with Flask. Migrate JSON state → SQLite. **Complete.**

---

### ✅ Phase 2 — Standby clock + active hours
**Goal:** Standby is the default view. Clock displays. During active hours it rotates to habits. **Complete.**

---

### ✅ Phase 3 — Habits page
**Goal:** Clean habits checklist. Button per habit, streak shown. Only today's habits visible. **Complete.**

---

### Phase 4 — Strava integration + Fitness page (running)
**Goal:** Run days auto-complete. Fitness page shows running data.

New file: `strava.py`

- [ ] Register Strava app, store tokens in `.env`, refresh via APScheduler
- [ ] `did_i_run_today() -> bool`
- [ ] `get_recent_runs() -> list[dict]`
- [ ] Hook into habits route: auto-complete "Run logged" if run detected
- [ ] `templates/fitness.html` — Plotly graph (distance/pace over time)

**Done when:** Running ticks the box automatically; fitness page shows data.

---

### Phase 5 — Hevy integration (weights)
**Goal:** Workout days auto-complete. Fitness page extended with weights data.

New file: `hevy.py`

- [ ] Hevy API key in `.env`
- [ ] `did_i_lift_today() -> bool`
- [ ] `get_recent_workouts() -> list[dict]`
- [ ] Hook into habits route: auto-complete "Workout logged"
- [ ] Extend `templates/fitness.html` with volume/PR graphs

**Done when:** Logging in Hevy ticks the box; page shows workout graphs.

---

### Phase 6 — Budget page (TrueLayer)
**Goal:** Category budgets vs actual spend, with burn-rate visualisation.

#### ✅ Infrastructure complete
- TrueLayer OAuth (PKCE + CSRF state) for Monzo, Nationwide, Amex
- Tokens in SQLite with `expires_at`; per-request refresh, APScheduler backstop
- `get_transactions(provider) -> list[dict]` — last 30 days
- Sandbox mode via `TRUELAYER_SANDBOX=true` in `.env`; switch to production by setting `false` and updating credentials

#### Remaining — budget UI
The current charts (spend-by-category bar, daily total line) are placeholder. The real page design:

**What the user wants to see:**
- Per-category budget limits set by the user, compared against actual spend for the month
- A line graph showing cumulative spend per category over the month — the slope reveals burn rate
- Toggles: month view (default), year view, projection to end of period

**Design decisions:**
- **Budget limits live in `config.py`** — simple dict mapping category name → monthly limit. No UI editor needed yet; editing the file is fine.
- **Category mapping layer** — TrueLayer returns its own taxonomy (`transaction_classification`, e.g. `["Food", "Groceries"]`). A mapping layer in `truelayer.py` or a new `budget.py` translates these to the user's personal categories (travel, food, restaurants, rent, subscriptions, etc.). Some will be 1:1; a catch-all "Other" handles the rest.
- **Projection** — extrapolate current daily spend rate to end of month/year. Only meaningful after a few days of data; show a dashed line.
- **Line graph is the primary visualisation** — one line per category, x-axis is days of month, y-axis is cumulative spend, horizontal dotted line marks the budget limit.

**Done when:** Budget page shows each category's spend vs limit, burn-rate line graph, with month/year/projection toggle.

---

### Phase 7 — Raspberry Pi deployment
**Goal:** Headless autostart, kiosk browser.

- [ ] Install all deps on Pi
- [ ] systemd service for Flask (or gunicorn)
- [ ] Chromium kiosk mode pointing at `localhost:5000`
- [ ] Test all integrations on Pi hardware

**Done when:** Pi boots straight into the dashboard, no keyboard needed.

---

## Conventions

- All credentials go in `.env` — never hardcode, never commit
- `dashboard.db` and `.env` are gitignored
- Each integration has one job: return a bool or a list. No UI logic in integrations.
- If an integration fails, log the error and fall back to manual button — never crash the app
- All business logic in Python — keep Jinja templates thin
- No external CSS frameworks — plain CSS only

---

## Running the app

```bash
# Install
uv sync

# Run
flask --app src/good_start_habits/app.py run
```
