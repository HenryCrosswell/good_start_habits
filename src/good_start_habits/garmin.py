"""Garmin Connect integration — activity sync, EF calculation, LLM coaching summary."""

import json
import logging
import os
import sqlite3
import time
from datetime import date

log = logging.getLogger(__name__)

GARMIN_TOKENS_DIR: str = os.environ.get(
    "GARMIN_TOKENS_DIR", os.path.expanduser("~/.garth")
)
SYNC_START_DATE = date(2026, 1, 1)


def _get_client():
    """Return an authenticated Garmin client, or None if credentials unavailable."""
    try:
        from garminconnect import Garmin

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

        # Skip already-stored activities
        if db.execute(
            "SELECT 1 FROM garmin_activities WHERE activity_id = ?", (act_id,)
        ).fetchone():
            continue

        start = act.get("startTimeLocal", "")
        act_date = start[:10] if start else ""
        name = act.get("activityName", "")
        max_hr = act.get("maxHR") or 0.0
        duration = act.get("duration") or 0.0
        calories = int(act.get("calories") or 0)

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
                 ef, run_pace_s_per_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
               ef, run_pace_s_per_km
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
        margin=dict(l=55, r=15, t=20, b=40),
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
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=14)),
        hovermode="x unified",
    )

    return plotly.io.to_json(fig, remove_uids=True)


# ---------------------------------------------------------------------------
# LLM coaching summary
# ---------------------------------------------------------------------------


def generate_summary(db: sqlite3.Connection, activities: list[dict]) -> str:
    """Return a cached LLM coaching summary, regenerating only when a new activity is stored.

    Returns '' if no API key is set, or '__retry__' if the API is temporarily unavailable.
    """
    ef_runs = [a for a in activities if a["ef"] is not None]
    if not ef_runs:
        return ""

    latest_id = ef_runs[-1]["activity_id"]

    cached = db.execute(
        "SELECT summary, last_activity_id FROM garmin_summaries ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if cached and cached[1] == latest_id:
        return cached[0]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    recent = ef_runs[-10:]
    if len(ef_runs) >= 2:
        trend = f"{(ef_runs[-1]['ef'] - ef_runs[0]['ef']) / ef_runs[0]['ef'] * 100:+.1f}% since first run"
    else:
        trend = "first run on record"

    context = json.dumps(
        {
            "runs": [
                {
                    "date": a["date"],
                    "ef": a["ef"],
                    "hr": a["avg_hr"],
                    "pace": a["run_pace"],
                    "dist_km": a["distance_km"],
                    "run_km": a["run_distance_km"],
                }
                for a in recent
            ],
            "total_runs": len(ef_runs),
            "ef_trend": trend,
        },
        separators=(",", ":"),
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=[
                {
                    "type": "text",
                    "text": (
                        "You are a friendly personal running coach. Given compact JSON running stats, "
                        "write 100-150 words: highlight 2-3 specific observations from the numbers, "
                        "then give one actionable tip. Be encouraging but honest. Plain text only."
                    ),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": context}],
        )
        summary = msg.content[0].text
        db.execute(
            "INSERT INTO garmin_summaries (generated_at, last_activity_id, summary)"
            " VALUES (datetime('now'), ?, ?)",
            (latest_id, summary),
        )
        db.commit()
        return summary
    except Exception as exc:
        log.warning("LLM summary failed: %s", exc)
        err = str(exc).lower()
        if any(k in err for k in ("rate", "limit", "credit", "overload", "529")):
            return "__retry__"
        return ""
