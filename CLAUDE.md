# good-start-habits — CLAUDE.md

A personal habit accountability dashboard. Starts simple, grows over time.
Built in Python, runs in the browser via Streamlit, ports to Raspberry Pi later.

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
| Language | Python 3.11+ | Only language needed |
| UI | Streamlit | Python-native browser UI, Pi-friendly |
| State | JSON file | Simple, readable, no database needed yet |
| Config | config.py | Plain Python dict, easy to edit |

---

## Project Structure

```
src/good_start_habits/
├── __init__.py       # inits project file
├── app.py            # Streamlit UI — the whole app
├── config.py         # Your habits, schedule, active hours
├── habits.py         # Streak logic, state load/save
├── state.json        # Auto-created. Tracks streaks + today's completions
```

New files are added per phase. Nothing is deleted — only extended.

---

## Habits (defined in config.py)

| Habit | Trigger | How it completes |
|---|---|---|
| SPF applied | Morning | Button |
| Vitamins & Omega-3 | Morning | Button |
| Log meal | Meal times | Button (API later) |
| Piano practice | Daily | Button |
| Journal entry | Daily | Button |
| Neuroscience notes | Daily | Button |
| Check to-do book | Daily | Button |
| Workout logged | Exercise days | Button (Hevy API later) |
| Run logged | Run days | Button (Strava API later) |

---

## Escalation Levels (time since reminder appeared)

| Time pending | Level | Visual |
|---|---|---|
| 0–15 min | 1 | Grey — subtle |
| 15–30 min | 2 | Amber — soft nudge |
| 30–60 min | 3 | Red — urgent |
| 60+ min | 4 | Flashing red — aggressive |

---

## Build Phases

### ✅ Phase 1 — Core app (start here)
**Goal:** A working checklist with streaks that saves state.

Files: `app.py`, `config.py`, `habits.py`, `state.json`

- [ ] `config.py` — define habits as a list of dicts (name, icon, time)
- [ ] `habits.py` — load/save state.json, mark habit done, get streak
- [ ] `app.py` — Streamlit UI, one button per habit, streak shown next to each
- [ ] State resets each day automatically (check date on load)

**Done when:** You can tick off habits, streaks increment, data survives a restart.

---

### Phase 2 — Active hours + escalation
**Goal:** App only shows reminders during your active hours. Urgency grows over time.

Changes to: `app.py`, `config.py`

- [ ] Add active hours to `config.py` (per day of week)
- [ ] Show a sleep screen outside active hours
- [ ] Calculate escalation level from time habit became due
- [ ] Apply colour coding to each habit card (grey → amber → red)
- [ ] Add `st.rerun()` loop so the page refreshes automatically

**Done when:** App goes quiet at night, colours shift as time passes.

---

### Phase 3 — Strava integration
**Goal:** Run days auto-complete when Strava detects an activity.

New file: `integrations/strava.py`

- [ ] Register a Strava API app (free)
- [ ] OAuth token saved locally to `.env`
- [ ] `strava.py` — single function: `did_i_run_today() -> bool`
- [ ] Hook into `app.py` — if run detected, habit auto-completes

**Done when:** Going for a run ticks the box without touching the app.

---

### Phase 4 — Hevy integration
**Goal:** Workout days auto-complete when Hevy detects a session.

New file: `integrations/hevy.py`

- [ ] Hevy API key (check docs.hevy.com)
- [ ] `hevy.py` — single function: `did_i_lift_today() -> bool`
- [ ] Hook into `app.py`

**Done when:** Logging a workout in Hevy ticks the box.

---

### Phase 5 — MyFitnessPal
**Goal:** Meal reminders auto-close when MFP has an entry.

New file: `integrations/mfp.py`

- [ ] Try `myfitnesspal` Python library first
- [ ] Fallback: keep as manual button if API proves unreliable
- [ ] `mfp.py` — `did_i_log_a_meal_today() -> bool`

**Done when:** Logging in MFP ticks the meal box (or manual button stays — that's fine).

---

### Phase 6 — LLM coaching
**Goal:** After a run, get brief feedback. On demand, get meal suggestions.

New file: `integrations/claude_coach.py`

- [ ] Anthropic SDK installed (`pip install anthropic`)
- [ ] API key in `.env`
- [ ] `get_run_feedback(activity_data, goals) -> str`
- [ ] `get_meal_suggestion(known_meals, time_of_day) -> str`
- [ ] Small panel in `app.py` to show coaching output

**Done when:** A post-run note appears on the dashboard after Strava syncs.

---

### Phase 7 — Raspberry Pi deployment
**Goal:** App runs headlessly on Pi, launches on boot, displays on screen.

- [ ] `pip install` everything on Pi
- [ ] Create systemd service for `streamlit run app.py`
- [ ] Chromium kiosk mode pointing at `localhost:8501`
- [ ] Test all integrations on Pi hardware

**Done when:** Pi boots straight into the dashboard with no keyboard needed.

---

## Conventions

- All credentials go in `.env` — never hardcode, never commit
- `state.json` and `.env` are gitignored
- Each integration has one job: return a bool or a string. No UI logic in integrations.
- If an integration fails, log the error and fall back to manual button — never crash the app

---

## Running the app

```bash
# Install
pip install streamlit

# Run
streamlit run app.py
```
