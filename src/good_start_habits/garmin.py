"""Garmin Connect integration — activity sync, EF calculation, LLM coaching summary."""

import json
import logging
import os
import sqlite3
import time
from datetime import date

log = logging.getLogger(__name__)

GARMIN_TOKENS_DIR: str = os.environ.get(
    "GARMIN_TOKENS_DIR", os.path.expanduser("~/.garminconnect")
)
SYNC_START_DATE = date(2026, 1, 1)

# EF reference: recreational male ~28yr at easy aerobic pace (~5:30/km, ~155 bpm)
EF_BENCHMARK_28M = 0.070

_COACH_CONTEXT = """Fitness Coach Prompt — Henry
You are my personal trainer and accountability coach. Refer to this context every response. State the mode (BEFORE / AFTER / WEEKLY / MISSED) at the top.

RACE GOAL
Half marathon — 14 June 2026. All training serves arriving healthy and ready.

STATUS
182cm, ~79–81kg (creatine water weight; target 76kg)
Body recomposition: lose fat, build visible muscle — not just chase the scale
UK-based (Aldi / Lidl / Tesco for food)
Desk job 8:00–4:30, all training between 6:50–8:00am
~10 yrs inconsistent training; functionally beginner
Tracked: Hevy (gym), Garmin + Strava (run)

COACH'S ASSESSMENT (read this first)
Working well
HR-based easy runs are landing — three Base sessions in a row 22–25 April (HR 140–144). This is the first real aerobic base block. Hold the discipline.
Interval average is now controlled (5:06/km on 30 Apr).
Diagnosis of set-3 collapse as a rest issue is correct.

Top risks (priority order)
Long-run volume gap. Only one 10km+ run all year (10.09km, 19 Apr). Plan jumps 12 → 14 → 16 → 18km in four weekends. The 12km on 3 May is the diagnostic. If form falls apart past 9km or HR runs away above 160 in the second half, hold at 13km next weekend rather than jumping to 14.
Interval pace creep — per-rep, not average. 30 Apr best rep was 4:13/km despite a 5:06 average. Slow reps masked fast ones. Enforce 5:15/km floor on EVERY rep, not just on average. Watch check every ~100m.
Posterior chain neglect. Workout B keeps slipping. Right adductor + calves + lower-leg ache all point to glutes/hamstrings not loading enough as run volume scales. Slot B once before 18 May, then drop it for taper.
Strength expectations are too steep for the block. Squat BW → 50kg and bench 22 → 30kg in 6 weeks while peaking mileage is unrealistic. Cap at +2.5kg per loaded lift per fortnight. Big jumps come post-race.
Cadence numbers in raw data are misleading. Walk breaks pull the average to 139–153 on easy/interval days; running cadence is 165–170 as planned. Read the cadence chart's running segments — don't false-flag the average.

Realistic HM finish: ~2:20–2:30 based on current 5K pace and long-run HR. First HM — finishing healthy is the goal.

WEEKLY STRUCTURE
Mon: Rest
Tue: Easy run, HR ≤153
Wed: Workout A
Thu: Intervals or tempo
Fri: Workout C
Sat: Long run, HR ≤155
Sun: Rest
Workout B unscheduled — slot once before 18 May. Never on a Friday before Sat long run.

STRENGTH
Hard rules
2–3 min rest between EVERY set. Set-3 collapse = rest, not strength — flag it.
≤40 min per session.
No Smith machine deadlifts.
DB row cue: depress shoulder blade first, drive elbow past hip, 1-sec squeeze. If felt in arms, drop weight + 3-sec tempo.

Workout A — Wed (lower / push)
Squat: 3 sets, current bodyweight, target 50kg
Bench (DB): 3 sets, current 22kg, target 30kg
DB row: 3 sets, current 18kg
Tricep ext (cable): 3 sets, current 10kg

Workout B — unscheduled (compound)
Deadlift: 3 sets, baseline TBD, barbell only
OHP (DB): 3 sets, 10kg
Lunge (DB): 3 sets, 10kg — monitor right adductor
Plank: 1 set, 30 sec

Workout C — Fri (pull / posture)
Lat pulldown: 3 sets, current 40kg, target 50kg
Incline bench (DB): 3 sets, current 16kg, target 25kg
Negative pull-ups: 3×5, 5-sec descent
Hanging knee raises: 3 sets

RUNNING
Baselines
5K pace 6:10–6:20/km | long-run pace ~6:54/km | resting HR 53 | max HR 195 | HRV ~48ms
Aerobic ceiling (Garmin zone 2): 153 bpm
Cadence 165–170 spm while running (180-rule does NOT apply at 182cm). Easy 163–167 / Tempo 168–172 / Intervals 172–176. Walk breaks drag the average — always read the chart, not the headline number.

Tuesday — easy
HR ≤153. Walk when ceiling hit, resume at ~140. Pace irrelevant.
Fasted OK <60 min. Porridge if >60 min.

Thursday A — 8×400m intervals
Pace cap 5:15–5:30/km — every rep, hard cap.
Flag immediately if any rep drops below 5:00/km.
Target HR ~175. Recovery 90 sec–2 min walk. 5–8 min warmup, 5 min cooldown.

Thursday B — tempo
HR 165–175 sustained, pace ~5:30–5:45/km.

Saturday — long run
HR ≤155. Conversational. Walk uphills to manage HR (strategy, not failure). Porridge beforehand — never fasted.

Garmin label check: easy runs should read "Base (Low Aerobic)". "Threshold" or "Tempo" = too hard.

NUTRITION
Protein 170g/day | ~2,000 kcal
Mostly chicken + veg, minimal red meat
Heavy dairy currently — fallback swaps: tinned tuna (~25g/tin, ~80p), Aldi/Lidl cooked chicken pouches, quark vs Greek yoghurt

Meals:
Porridge + 1–1.5 scoop whey + fruit: 28–30g protein
Post-WO shake (1.5 scoop + Greek yog + milk): 45–50g protein
½ chicken breast + chickpeas + wholewheat pasta: 35–40g protein
2 soft-boiled eggs: 12–13g protein
Dinner (chicken + veg, partner-cooked): ~20g protein
Evening protein yog: 15–20g protein
Good day total: 155–165g

Drop days = no eggs / no evening yog → 120–130g. Nudge those.
Supplements: creatine 10g/day (since 14 Apr — do NOT push to change), omega-3, A–Z multivit.
MFP: unsustainable daily — one tracking week, then occasional spot-checks.
Weighing: mornings, post-toilet, pre-eating. Scale up post-creatine = water + glycogen, not fat.

INJURY / READINESS FLAGS
Right anterior lower leg — dull ache after 10km. Sharp/localised = stop and flag.
Right adductor / inner hamstring — pulls on lunges. Dynamic warmup before loading; static stretch after.
Calves — tight after long runs. 3×15 calf raises daily, bent-knee stretch post-run.
Toe balance test — daily readiness check before runs. Sharp pain or can't perform = rest.
Posture — 5 wall slides + 10 chin tucks daily. 20/20/20 for screens. Remind before each gym session.

9-WEEK TIMELINE
Wk 1 (16–20 Apr) ✓: tempo + 10km, Workout A
Wk 2 (21–27 Apr) ✓: 7km easy deload, A partial + B partial
Wk 3 (28 Apr–4 May): 12km Sat, A + C
Wk 4 (5–11 May): 14km, A + C
Wk 5 (12–18 May): 16km, A + C (upper focus)
Wk 6 (19–25 May): 18km, A reduced + C upper only
Wk 7 (26 May–1 Jun): 14km, A light only
Wk 8 (2–8 Jun): 10km taper, no gym
Wk 9 (9–14 Jun): race week, no gym
14 Jun: HALF MARATHON

RECENT TRAINING
17 Apr: Tempo 25 min — HR 174, cad 169. Late hill sprint → max 195.
19 Apr: 10km easy — HR 163, cad 163. Too high — base still developing.
21 Apr: Workout A (upper only) — Bench 22×12/10/5, Row 18×8×3. Skipped squats, rest too short.
22 Apr: Workout B (partial) — OHP 10×10/12/10, Lunge 10×6/9/6. Right adductor tight.
22 Apr: 20 min — HR 142 ✅ Base. First clean easy run.
23 Apr: 30 min — HR 140 ✅ Base. Walk breaks working.
25 Apr: 7km easy — HR 144 ✅ Base. 3rd Base in a row.
30 Apr: 8×400m — avg 5:06/km, HR 165, best rep 4:13. Best rep too fast — 5:15/km floor next time.

HOW TO COACH
Tone: supportive but firm. Believe in him. No toxic positivity, no lectures. Short, direct, warm.
Missed session: ask why ONCE → adapt the week, no guilt. One = noise. Pattern = problem.
Always proactively flag: bad pacing, short rests, fast lift jumps, low protein, run volume jumps.
Recomp realism: visible change at 8–12 weeks. Markers = weekly fasted weigh-in, monthly photos, strength PRs (first loaded squat, bench ≥25kg), pace at same HR, Garmin labels shifting "Threshold" → "Base".

CHECK-IN MODES
BEFORE SESSION: confirm today's plan. Cues: rest periods (gym), pace cap + cadence (run), posture reminder.
AFTER SESSION: review stats. PR or concern. ONE actionable tweak.
WEEKLY REVIEW: ask weight / sessions done vs planned / best moment / hardest moment. Brief summary + ONE focus next week. Surface red flags.
MISSED: one question, acknowledge, adjust.

POST RACE (after 14 Jun 2026)
Gym → 3 days/week
Running → 2 days/week
New programme to be built post-race"""


def _bootstrap_tokens() -> None:
    """Write GARMIN_TOKEN_JSON env var content to the token directory if set.
    Allows Railway deployments to inject token material via an env var instead of
    requiring an interactive shell session to run the auth flow."""
    token_json = os.environ.get("GARMIN_TOKEN_JSON")
    if not token_json:
        return
    os.makedirs(GARMIN_TOKENS_DIR, exist_ok=True)
    token_path = os.path.join(GARMIN_TOKENS_DIR, "garmin_tokens.json")
    try:
        with open(token_path, "w") as f:
            f.write(token_json)
    except OSError as exc:
        log.warning("Could not write GARMIN_TOKEN_JSON to disk: %s", exc)


def _get_client():
    """Return an authenticated Garmin client, or None if credentials unavailable."""
    try:
        from garminconnect import Garmin

        _bootstrap_tokens()
        api = Garmin()
        api.login(tokenstore=GARMIN_TOKENS_DIR)
        return api
    except Exception as exc:
        log.warning("Garmin client unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Pure computation helpers
# ---------------------------------------------------------------------------


def _active_laps_stats(laps: list[dict]) -> tuple[float | None, float | None]:
    """Return (total_distance_m, total_duration_s) for ACTIVE laps only."""
    active = [lap for lap in laps if lap.get("intensityType") == "ACTIVE"]
    if not active:
        return None, None
    dist = sum(lap.get("distance", 0) or 0 for lap in active)
    dur = sum(lap.get("duration", 0) or 0 for lap in active)
    return (dist, dur) if dist and dur else (None, None)


def compute_ef(run_speed_mps: float, avg_hr: float) -> float | None:
    """Efficiency Factor = run speed (km/h) / avg heart rate."""
    if not avg_hr or avg_hr <= 0:
        return None
    return round((run_speed_mps * 3.6) / avg_hr, 5)


def _pace_str(sec_per_km: float) -> str:
    """Format seconds-per-km as 'M:SS'."""
    mins = int(sec_per_km // 60)
    secs = int(sec_per_km % 60)
    return f"{mins}:{secs:02d}"


def _pace_secs(pace_str: str | None) -> float | None:
    """Parse 'M:SS' string back to total seconds."""
    if not pace_str:
        return None
    try:
        parts = pace_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def _indicator(curr, prev, *, higher_is_better: bool = True) -> dict:
    """Return {pct, arrow, good} comparing curr to prev for template rendering."""
    if curr is None or prev is None or prev == 0:
        return {"pct": None, "arrow": "", "good": None}
    diff = curr - prev
    if abs(diff / prev) < 0.001:
        return {"pct": 0.0, "arrow": "—", "good": None}
    pct = abs(diff / prev) * 100
    going_up = diff > 0
    good = going_up == higher_is_better
    return {"pct": round(pct, 1), "arrow": "▲" if going_up else "▼", "good": good}


# ---------------------------------------------------------------------------
# DB sync
# ---------------------------------------------------------------------------


def backfill_cadence(db: sqlite3.Connection) -> int:
    """Fetch all activities since SYNC_START_DATE and fill null cadence values. Returns count updated."""
    client = _get_client()
    if not client:
        return 0
    null_count = db.execute(
        "SELECT COUNT(*) FROM garmin_activities WHERE avg_cadence_spm IS NULL"
    ).fetchone()[0]
    if not null_count:
        return 0
    try:
        raw_activities = client.get_activities_by_date(
            SYNC_START_DATE.isoformat(), date.today().isoformat(), "running"
        )
    except Exception as exc:
        log.error("Cadence backfill fetch failed: %s", exc)
        return 0
    updated = 0
    for act in raw_activities:
        act_id = act.get("activityId")
        cadence = act.get("averageRunningCadenceInStepsPerMinute") or None
        if not act_id or cadence is None:
            continue
        result = db.execute(
            "UPDATE garmin_activities SET avg_cadence_spm = ? WHERE activity_id = ? AND avg_cadence_spm IS NULL",
            (cadence, act_id),
        )
        updated += result.rowcount
    if updated:
        db.commit()
    log.info("Cadence backfill: %d activities updated", updated)
    return updated


def sync_activities(db: sqlite3.Connection) -> int:
    """Fetch new running activities from Garmin and persist them. Returns count inserted."""
    client = _get_client()
    if not client:
        return 0

    row = db.execute("SELECT MAX(activity_date) FROM garmin_activities").fetchone()
    since = row[0] if (row and row[0]) else SYNC_START_DATE.isoformat()
    today = date.today().isoformat()

    try:
        raw_activities = client.get_activities_by_date(since, today, "running")
    except Exception as exc:
        log.error("Garmin activity fetch failed: %s", exc)
        return 0

    added = 0
    for act in raw_activities:
        act_id = act.get("activityId")
        if not act_id:
            continue

        dist = act.get("distance") or 0.0
        avg_hr = act.get("averageHR") or 0.0

        # Skip MyFitnessPal imports and activities missing GPS or HR
        if not dist or not avg_hr:
            continue

        start = act.get("startTimeLocal", "")
        act_date = start[:10] if start else ""
        name = act.get("activityName", "")
        max_hr = act.get("maxHR") or 0.0
        duration = act.get("duration") or 0.0
        calories = int(act.get("calories") or 0)
        avg_cadence = act.get("averageRunningCadenceInStepsPerMinute") or None

        # Skip already-stored activities, but backfill cadence if it was missing
        existing = db.execute(
            "SELECT avg_cadence_spm FROM garmin_activities WHERE activity_id = ?",
            (act_id,),
        ).fetchone()
        if existing is not None:
            if existing[0] is None and avg_cadence is not None:
                db.execute(
                    "UPDATE garmin_activities SET avg_cadence_spm = ? WHERE activity_id = ?",
                    (avg_cadence, act_id),
                )
                db.commit()
            continue

        # Fetch splits for run-only pace (ACTIVE laps, excludes walk-break laps)
        run_dist = run_dur = ef = run_pace_s = None
        try:
            time.sleep(0.3)  # gentle rate-limiting
            splits = client.get_activity_splits(act_id)
            laps = splits.get("lapDTOs", splits.get("laps", []))
            run_dist, run_dur = _active_laps_stats(laps)
        except Exception as exc:
            log.warning("Splits unavailable for activity %s: %s", act_id, exc)

        if run_dist and run_dur and avg_hr:
            run_speed = run_dist / run_dur  # m/s
            ef = compute_ef(run_speed, avg_hr)
            run_pace_s = run_dur / (run_dist / 1000)  # s/km
        elif dist and duration and avg_hr:
            # Fallback: total activity speed (less accurate for run/walk intervals)
            ef = compute_ef(dist / duration, avg_hr)
            run_pace_s = duration / (dist / 1000) if dist else None

        db.execute(
            """
            INSERT OR IGNORE INTO garmin_activities
                (activity_id, activity_date, name, distance_meters, duration_seconds,
                 avg_hr_bpm, max_hr_bpm, calories, run_distance_m, run_duration_s,
                 ef, run_pace_s_per_km, avg_cadence_spm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                act_id,
                act_date,
                name,
                dist,
                duration,
                avg_hr,
                max_hr,
                calories,
                run_dist,
                run_dur,
                ef,
                run_pace_s,
                avg_cadence,
            ),
        )
        db.commit()
        added += 1

    log.info("Garmin sync: %d new activities added", added)
    return added


# ---------------------------------------------------------------------------
# Read / compute
# ---------------------------------------------------------------------------


def get_all_activities(db: sqlite3.Connection) -> list[dict]:
    """Return all stored running activities as dicts, oldest first."""
    rows = db.execute(
        """
        SELECT activity_id, activity_date, name, distance_meters, duration_seconds,
               avg_hr_bpm, max_hr_bpm, calories, run_distance_m, run_duration_s,
               ef, run_pace_s_per_km, avg_cadence_spm
        FROM garmin_activities
        ORDER BY activity_date ASC
        """
    ).fetchall()

    result = []
    for r in rows:
        run_pace_s = r[11]
        result.append(
            {
                "activity_id": r[0],
                "date": r[1],
                "name": r[2],
                "distance_km": round(r[3] / 1000, 2) if r[3] else None,
                "duration_min": round(r[4] / 60, 1) if r[4] else None,
                "avg_hr": r[5],
                "max_hr": r[6],
                "calories": r[7],
                "run_distance_km": round(r[8] / 1000, 2) if r[8] else None,
                "ef": round(r[10], 4) if r[10] else None,
                "run_pace": _pace_str(run_pace_s) if run_pace_s else None,
                "cadence_spm": round(r[12]) if r[12] else None,
            }
        )
    return result


def get_latest_run_stats(activities: list[dict]) -> dict | None:
    """Return latest run stats with delta indicators vs the previous run."""
    ef_runs = [a for a in activities if a["ef"] is not None]
    if not ef_runs:
        return None

    latest = ef_runs[-1]
    prev = ef_runs[-2] if len(ef_runs) >= 2 else None

    def _p(key):
        return prev[key] if prev else None

    latest_pace_s = _pace_secs(latest.get("run_pace"))
    prev_pace_s = _pace_secs(_p("run_pace"))

    return {
        **latest,
        "ef_ind": _indicator(latest["ef"], _p("ef"), higher_is_better=True),
        "hr_ind": _indicator(latest["avg_hr"], _p("avg_hr"), higher_is_better=False),
        "pace_ind": _indicator(latest_pace_s, prev_pace_s, higher_is_better=False),
        "dist_ind": _indicator(
            latest["distance_km"], _p("distance_km"), higher_is_better=True
        ),
    }


def build_ef_chart(activities: list[dict]) -> str:
    """Return Plotly JSON string for the EF-over-time chart."""
    import plotly
    import plotly.graph_objects as go

    ef_acts = [a for a in activities if a["ef"] is not None]
    if not ef_acts:
        return ""

    dates = [a["date"] for a in ef_acts]
    efs = [a["ef"] for a in ef_acts]

    # 5-run rolling average
    w = 5
    rolling = [
        sum(efs[max(0, i - w + 1) : i + 1]) / len(efs[max(0, i - w + 1) : i + 1])
        for i in range(len(efs))
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=efs,
            mode="lines+markers",
            name="EF per run",
            line=dict(color="#FF6B00", width=2),
            marker=dict(size=9, color="#FF6B00"),
            hovertemplate="%{x}<br>EF: %{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=rolling,
            mode="lines",
            name=f"{w}-run avg",
            line=dict(color="#9B30FF", width=2, dash="dot"),
            hovertemplate="%{x}<br>avg: %{y:.4f}<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="VT323, monospace", size=16, color="#111111"),
        margin=dict(l=60, r=15, t=30, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor="#E0D8CC",
            linecolor="#111111",
            tickfont=dict(size=13),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#E0D8CC",
            linecolor="#111111",
            tickformat=".3f",
            title="EF",
            tickfont=dict(size=13),
        ),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(size=14)),
        hovermode="x unified",
        shapes=[
            {
                "type": "line",
                "xref": "paper",
                "yref": "y",
                "x0": 0,
                "x1": 1,
                "y0": EF_BENCHMARK_28M,
                "y1": EF_BENCHMARK_28M,
                "line": {"color": "#AAAAAA", "width": 1.5, "dash": "dot"},
            }
        ],
        annotations=[
            {
                "xref": "paper",
                "yref": "y",
                "x": 0.01,
                "y": EF_BENCHMARK_28M,
                "text": "avg peer",
                "showarrow": False,
                "font": {"size": 11, "color": "#888888", "family": "VT323, monospace"},
                "xanchor": "left",
                "yanchor": "bottom",
            }
        ],
    )

    return plotly.io.to_json(fig, remove_uids=True)


# ---------------------------------------------------------------------------
# LLM coaching summaries — activity / week / month
# ---------------------------------------------------------------------------


def _lm_bullets(api_key: str, system_text: str, user_json: str, max_tokens: int) -> str:
    """Call Haiku with a cached system prompt. Returns bullet text, '' or '__retry__'."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": _COACH_CONTEXT,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": system_text,
                },
            ],
            messages=[{"role": "user", "content": user_json}],
        )
        block = msg.content[0]
        return block.text.strip() if hasattr(block, "text") else ""
    except Exception as exc:
        log.warning("LLM call failed: %s", exc)
        err = str(exc).lower()
        return (
            "__retry__"
            if any(k in err for k in ("rate", "limit", "credit", "overload", "529"))
            else ""
        )


def _cached_summary(
    db: sqlite3.Connection, summary_type: str, period_key: str
) -> str | None:
    row = db.execute(
        "SELECT summary FROM garmin_summaries WHERE summary_type=? AND period_key=? ORDER BY id DESC LIMIT 1",
        (summary_type, period_key),
    ).fetchone()
    return row[0] if row else None


def _store_summary(
    db: sqlite3.Connection,
    latest_id: int | None,
    summary_type: str,
    period_key: str,
    summary: str,
) -> None:
    db.execute(
        "INSERT INTO garmin_summaries (generated_at, last_activity_id, summary_type, period_key, summary)"
        " VALUES (datetime('now'), ?, ?, ?, ?)",
        (latest_id, summary_type, period_key, summary),
    )
    db.commit()


def generate_activity_summary(db: sqlite3.Connection, activities: list[dict]) -> str:
    """3-bullet review of the most recent run. Cached until a new activity appears."""
    ef_runs = [a for a in activities if a["ef"] is not None]
    if not ef_runs:
        return ""

    latest = ef_runs[-1]
    period_key = str(latest["activity_id"])
    cached = _cached_summary(db, "activity", period_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    prev = ef_runs[-2] if len(ef_runs) >= 2 else None
    context = json.dumps(
        {
            "date": latest["date"],
            "ef": latest["ef"],
            "ef_peer_benchmark": EF_BENCHMARK_28M,
            "hr_avg": latest["avg_hr"],
            "hr_max": latest["max_hr"],
            "pace": latest["run_pace"],
            "dist_km": latest["distance_km"],
            "run_km": latest["run_distance_km"],
            "prev_ef": prev["ef"] if prev else None,
            "prev_pace": prev["run_pace"] if prev else None,
        },
        separators=(",", ":"),
    )

    system = (
        "You are a concise running coach. Write exactly 3 bullet points, each starting with '• '. "
        "Max 12 words per bullet. Cover: (1) EF vs peer benchmark and vs previous run, "
        "(2) pace or HR observation with the specific number, "
        "(3) one concrete actionable tip for the next run. "
        "No intro line. Numbers only — no vague language."
    )

    result = _lm_bullets(api_key, system, context, max_tokens=110)
    if result and result != "__retry__":
        _store_summary(db, latest["activity_id"], "activity", period_key, result)
    return result


def generate_week_summary(db: sqlite3.Connection, activities: list[dict]) -> str:
    """3-bullet week-in-review. Regenerates once per ISO calendar week."""
    from datetime import timedelta

    today = date.today()
    iso = today.isocalendar()
    period_key = f"{iso.year}-W{iso.week:02d}"

    ef_runs = [a for a in activities if a["ef"] is not None]
    if not ef_runs:
        return ""

    cached = _cached_summary(db, "week", period_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    week_start = (today - timedelta(days=6)).isoformat()
    week_runs = [a for a in ef_runs if a["date"] >= week_start]
    if not week_runs:
        return ""

    prev_week_start = (today - timedelta(days=13)).isoformat()
    prev_week_runs = [a for a in ef_runs if prev_week_start <= a["date"] < week_start]
    prev_avg_ef = (
        round(sum(a["ef"] for a in prev_week_runs) / len(prev_week_runs), 4)
        if prev_week_runs
        else None
    )

    context = json.dumps(
        {
            "week": period_key,
            "runs_this_week": len(week_runs),
            "total_km": round(sum(a["distance_km"] or 0 for a in week_runs), 1),
            "ef_values": [a["ef"] for a in week_runs],
            "ef_peer_benchmark": EF_BENCHMARK_28M,
            "paces": [a["run_pace"] for a in week_runs if a["run_pace"]],
            "prev_week_runs": len(prev_week_runs),
            "prev_week_avg_ef": prev_avg_ef,
        },
        separators=(",", ":"),
    )

    system = (
        "You are a running coach writing a weekly summary. Write exactly 3 bullet points, each starting with '• '. "
        "Max 15 words per bullet. Cover: "
        "(1) volume and consistency vs previous week, "
        "(2) EF trend this week vs peer benchmark, "
        "(3) one specific focus for next week. "
        "No intro line. Use the numbers, be direct."
    )

    result = _lm_bullets(api_key, system, context, max_tokens=120)
    if result and result != "__retry__":
        _store_summary(db, ef_runs[-1]["activity_id"], "week", period_key, result)
    return result


def generate_month_summary(db: sqlite3.Connection, activities: list[dict]) -> str:
    """4-bullet review of the previous calendar month."""
    today = date.today()
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    period_key = f"{year}-{month:02d}"

    ef_runs = [a for a in activities if a["ef"] is not None]
    if not ef_runs:
        return ""

    cached = _cached_summary(db, "month", period_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    month_runs = [a for a in ef_runs if a["date"].startswith(period_key)]
    if not month_runs:
        return ""

    first_ef = month_runs[0]["ef"]
    last_ef = month_runs[-1]["ef"]
    ef_change = round((last_ef - first_ef) / first_ef * 100, 1) if first_ef else None

    context = json.dumps(
        {
            "month": period_key,
            "total_runs": len(month_runs),
            "total_km": round(sum(a["distance_km"] or 0 for a in month_runs), 1),
            "ef_start": first_ef,
            "ef_end": last_ef,
            "ef_change_pct": ef_change,
            "ef_peer_benchmark": EF_BENCHMARK_28M,
            "best_ef": max(a["ef"] for a in month_runs),
            "avg_hr": round(
                sum(a["avg_hr"] or 0 for a in month_runs) / len(month_runs), 0
            ),
            "all_time_runs": len(ef_runs),
        },
        separators=(",", ":"),
    )

    system = (
        "You are a running coach writing a monthly review. Write exactly 4 bullet points, each starting with '• '. "
        "Max 15 words per bullet. Cover: "
        "(1) total volume and run count, "
        "(2) EF progression this month vs peer benchmark, "
        "(3) one clear strength, "
        "(4) one priority for next month. "
        "No intro line. Use the numbers, be direct."
    )

    result = _lm_bullets(api_key, system, context, max_tokens=140)
    if result and result != "__retry__":
        _store_summary(db, ef_runs[-1]["activity_id"], "month", period_key, result)
    return result


# ---------------------------------------------------------------------------
# Fitness stats — sync + display
# ---------------------------------------------------------------------------

# Average values for an untrained/recreational 28-year-old male
_BENCH_28M = {
    "fitness_age": 28,  # chronological = average
    "rhr": 65,  # bpm — avg sedentary male
    "hrv": 42,  # ms weekly avg (RMSSD proxy, Garmin scale)
    "bmi": 25.5,  # avg UK/AU 28yr male
    "cadence": 163,  # spm — avg recreational male runner (both feet combined)
}


def sync_fitness_stats(db: sqlite3.Connection) -> None:
    """Fetch fitness metrics from Garmin and cache in DB. Best-effort — any field may be absent."""
    client = _get_client()
    if not client:
        return

    today = date.today().isoformat()
    stats: dict = {}

    try:
        fa = client.get_fitnessage_data(today)
        if fa:
            # Raw API: biologicalAge / chronologicalAge
            # garminconnect ≥0.2 may wrap it differently; try both
            stats["fitness_age"] = fa.get("fitnessAge")
            comps = fa.get("components") or fa.get("fitnessAgeDataList") or []
            if isinstance(comps, dict):
                rhr_c = comps.get("rhr", {})
                stats["rhr"] = rhr_c.get("value") if isinstance(rhr_c, dict) else None
                bmi_c = comps.get("bmi", {})
                stats["bmi"] = bmi_c.get("value") if isinstance(bmi_c, dict) else None
    except Exception as exc:
        log.warning("Fitness age sync failed: %s", exc)

    try:
        hrv = client.get_hrv_data(today)
        if hrv:
            last = hrv.get("hrvSummary") or {}
            stats["hrv_weekly_avg"] = last.get("weeklyAvg")
            stats["hrv_status"] = last.get("status")
    except Exception as exc:
        log.warning("HRV sync failed: %s", exc)

    try:
        rhr_data = client.get_rhr_day(today)
        if rhr_data and not stats.get("rhr"):
            metrics = (rhr_data.get("allMetrics") or {}).get("metricsMap", {})
            rhr_list = metrics.get("WELLNESS_RESTING_HEART_RATE", [])
            if rhr_list:
                stats["rhr"] = rhr_list[0].get("value")
    except Exception as exc:
        log.warning("RHR sync failed: %s", exc)

    try:
        mx = client.get_max_metrics(today)
        if mx and isinstance(mx, list) and mx:
            stats["vo2max"] = (mx[0].get("generic") or {}).get("vo2MaxPreciseValue")
    except Exception as exc:
        log.warning("VO2 max sync failed: %s", exc)

    if not stats:
        return

    db.execute(
        "INSERT INTO garmin_fitness_cache (fetched_date, data) VALUES (?, ?)"
        " ON CONFLICT(fetched_date) DO UPDATE SET data=excluded.data, updated_at=datetime('now')",
        (today, json.dumps(stats)),
    )
    db.commit()
    log.info("Fitness stats cached: %s", stats)


def get_fitness_stats(db: sqlite3.Connection) -> dict:
    """Return most-recent cached fitness stats as a display-ready structure."""
    row = db.execute(
        "SELECT data FROM garmin_fitness_cache ORDER BY fetched_date DESC LIMIT 1"
    ).fetchone()
    raw: dict = {}
    if row:
        try:
            raw = json.loads(row[0])
        except Exception:
            pass

    def _stat(key: str, your_val, bench_val, unit: str, higher_is_better: bool) -> dict:
        if your_val is None:
            return {
                "label": key,
                "your": None,
                "bench": f"{bench_val}{unit}",
                "good": None,
                "arrow": "",
            }
        diff = your_val - bench_val
        going_up = diff > 0
        good = going_up == higher_is_better
        arrow = "▲" if going_up else "▼"
        if abs(diff) < 0.1:
            arrow, good = "—", None
        fmt = (
            f"{round(your_val, 1)}"
            if isinstance(your_val, float)
            else str(int(your_val))
        )
        return {
            "label": key,
            "your": f"{fmt}{unit}",
            "bench": f"{bench_val}{unit}",
            "good": good,
            "arrow": arrow,
        }

    # Compute average cadence from most recent 10 runs with cadence data
    cadence_val = None
    try:
        c_row = db.execute(
            "SELECT AVG(avg_cadence_spm) FROM ("
            "  SELECT avg_cadence_spm FROM garmin_activities"
            "  WHERE avg_cadence_spm IS NOT NULL"
            "  ORDER BY activity_date DESC LIMIT 10"
            ")"
        ).fetchone()
        if c_row and c_row[0]:
            cadence_val = round(c_row[0])
    except Exception:
        pass

    return {
        "fitness_age": _stat(
            "Fitness age",
            raw.get("fitness_age"),
            _BENCH_28M["fitness_age"],
            " yr",
            higher_is_better=False,
        ),
        "rhr": _stat(
            "Resting HR",
            raw.get("rhr"),
            _BENCH_28M["rhr"],
            " bpm",
            higher_is_better=False,
        ),
        "hrv": _stat(
            "HRV (weekly)",
            raw.get("hrv_weekly_avg"),
            _BENCH_28M["hrv"],
            " ms",
            higher_is_better=True,
        ),
        "bmi": _stat(
            "BMI", raw.get("bmi"), _BENCH_28M["bmi"], "", higher_is_better=False
        ),
        "cadence": _stat(
            "Cadence (avg)",
            cadence_val,
            _BENCH_28M["cadence"],
            " spm",
            higher_is_better=True,
        ),
    }


DAILY_CHAT_LIMIT = 5


def get_daily_chat_count(db: sqlite3.Connection) -> int:
    today = date.today().isoformat()
    row = db.execute(
        "SELECT COUNT(*) FROM garmin_chat_log WHERE asked_date = ?", (today,)
    ).fetchone()
    return row[0] if row else 0


def get_today_chat_history(db: sqlite3.Connection) -> list[dict]:
    today = date.today().isoformat()
    rows = db.execute(
        "SELECT question, response FROM garmin_chat_log WHERE asked_date = ? ORDER BY id ASC",
        (today,),
    ).fetchall()
    return [{"q": r[0], "r": r[1]} for r in rows]


def ask_trainer(
    db: sqlite3.Connection, activities: list[dict], question: str
) -> tuple[str | None, int]:
    """Ask the personal trainer chatbot.

    Returns (response, questions_used_today).
    response is None if the daily limit is reached, '' if the API is unavailable.
    """
    count = get_daily_chat_count(db)
    if count >= DAILY_CHAT_LIMIT:
        return None, count

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "", count

    lines = [
        f"{a['date']}: {a['distance_km']}km, pace {a['run_pace'] or '?'}/km, "
        f"avg HR {a['avg_hr']}bpm, EF {a['ef']}, cadence {a['cadence_spm'] or '?'}spm"
        for a in activities[-30:]
    ]
    session_context = (
        "You are a personal running coach. Answer questions using the athlete's recent data below. "
        "Be direct and specific. Never ask questions back. Under 100 words.\n\n"
        "Recent runs (oldest → newest):\n" + "\n".join(lines)
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=20.0)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=[
                {
                    "type": "text",
                    "text": _COACH_CONTEXT,
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": session_context},
            ],
            messages=[{"role": "user", "content": question}],
        )
        block = msg.content[0]
        response = block.text.strip() if hasattr(block, "text") else ""
        if not response:
            return "__error__", count
    except Exception as exc:
        log.warning("Trainer chat failed: %s", exc)
        return "__error__", count

    today = date.today().isoformat()
    db.execute(
        "INSERT INTO garmin_chat_log (asked_date, question, response) VALUES (?, ?, ?)",
        (today, question, response),
    )
    db.commit()
    return response, count + 1


def generate_next_run_plan(db: sqlite3.Connection, activities: list[dict]) -> str:
    """Specific next-run targets (distance, pace, HR) derived from recent run data.
    Cached until a new activity appears."""
    ef_runs = [a for a in activities if a["ef"] is not None]
    if len(ef_runs) < 2:
        return ""

    latest = ef_runs[-1]
    period_key = f"next_{latest['activity_id']}"
    cached = _cached_summary(db, "next_run", period_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    recent = ef_runs[-8:]
    context = json.dumps(
        {
            "runs": [
                {
                    "date": a["date"],
                    "distance_km": a["distance_km"],
                    "pace": a["run_pace"],
                    "avg_hr": a["avg_hr"],
                    "ef": a["ef"],
                    "cadence_spm": a.get("cadence_spm"),
                }
                for a in recent
            ],
            "ef_peer_benchmark": EF_BENCHMARK_28M,
        },
        separators=(",", ":"),
    )

    system = (
        "You are a running coach. Using ONLY the athlete's actual recent run data provided, "
        "output their next run targets. No generic advice — every number must come from or be "
        "directly derived from the data.\n\n"
        "Output EXACTLY 4 lines, no other text:\n"
        "Distance: <value>km\n"
        "Pace: <M:SS>/km\n"
        "HR ceiling: <value>bpm\n"
        "<one sentence, max 12 words, stating WHY using specific numbers from their recent runs>\n\n"
        "Rules: distance = their recent avg ±10% based on EF trend. "
        "Pace = their recent aerobic pace ±5s based on HR trend. "
        "HR ceiling = their recent avg HR rounded to nearest 5. "
        "No aspirational targets — only what their data supports."
    )

    result = _lm_bullets(api_key, system, context, max_tokens=80)
    if result and result != "__retry__":
        _store_summary(db, latest["activity_id"], "next_run", period_key, result)
    return result


def get_all_summaries(db: sqlite3.Connection, activities: list[dict]) -> dict:
    """Return all three coaching summaries plus a label for the month span."""
    import calendar as _cal

    today = date.today()
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1
    month_label = f"{_cal.month_abbr[prev_month]} {prev_year}"

    return {
        "activity": generate_activity_summary(db, activities),
        "week": generate_week_summary(db, activities),
        "month": generate_month_summary(db, activities),
        "month_label": month_label,
        "next_run": generate_next_run_plan(db, activities),
    }
