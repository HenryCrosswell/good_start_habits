"""Flask app — routes and startup."""

import atexit
import logging
import os
import sqlite3
from datetime import date, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, url_for

from good_start_habits import budget as budget_module  # noqa: E402
from good_start_habits import truelayer  # noqa: E402
from good_start_habits.config import (
    DWELL_TIME,
    PROVIDER_BUDGET_LIMITS,
    ROTATION_INTERVAL,
)  # noqa: E402
from good_start_habits.db import get_db, init_db  # noqa: E402
from good_start_habits.habits import (  # noqa: E402
    check_current_datetime,
    daily_maintenance,
    mark_done,
)

load_dotenv()

log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


# ---------------------------------------------------------------------------
# APScheduler — token refresh backstop
# ---------------------------------------------------------------------------

_scheduler = BackgroundScheduler()


def _refresh_tokens_job() -> None:
    con = sqlite3.connect("dashboard.db")
    try:
        truelayer.refresh_all(con)
    finally:
        con.close()


# Only start in the main Werkzeug process (not the file-watcher child)
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    _scheduler.add_job(_refresh_tokens_job, "interval", hours=1)
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown(wait=False))


# ---------------------------------------------------------------------------
# Request lifecycle
# ---------------------------------------------------------------------------


@app.before_request
def fire_up_db():
    init_db()


# ---------------------------------------------------------------------------
# Clock / standby
# ---------------------------------------------------------------------------


@app.route("/")
def clock():
    if check_current_datetime():
        return render_template(
            "clock.html",
            active=True,
            rotation_interval=ROTATION_INTERVAL,
        )
    return render_template("clock.html", active=False)


# ---------------------------------------------------------------------------
# Habits
# ---------------------------------------------------------------------------


@app.route("/habits")
def habits():
    db = get_db()
    daily_maintenance(db)
    habits = db.execute("SELECT name, streak, done_today FROM habits").fetchall()
    today = datetime.now().strftime("%A, %d %B %Y")
    return render_template(
        "habits.html", habits=habits, today=today, dwell_time=DWELL_TIME
    )


@app.route("/habits/<name>/done", methods=["POST"])
def habit_done(name: str):
    db = get_db()
    mark_done(db, name)
    return redirect(url_for("habits"))


@app.route("/habits/<name>/undo", methods=["POST"])
def habit_undo(name: str):
    db = get_db()
    mark_done(db, name, undo=True)
    return redirect(url_for("habits"))


# ---------------------------------------------------------------------------
# Budget — TrueLayer OAuth
# ---------------------------------------------------------------------------


@app.route("/auth/connect/<provider>")
def auth_connect(provider: str):
    if provider not in truelayer.PROVIDERS:
        abort(404)
    db = get_db()
    auth_url = truelayer.start_auth(db, provider)
    return redirect(auth_url)


@app.route("/auth/callback")
def auth_callback():
    if "error" in request.args:
        log.warning("TrueLayer auth error: %s", request.args.get("error"))
        return redirect(url_for("budget", flash="auth_cancelled"))

    code = request.args.get("code", "")
    state = request.args.get("state", "")

    if not code or not state:
        abort(400)

    db = get_db()
    provider, token_data = truelayer.finish_auth(db, code, state)

    if not provider or not token_data:
        return redirect(url_for("budget", flash="connect_failed"))

    truelayer.save_tokens(db, provider, token_data)
    return redirect(url_for("budget", flash=f"connected_{provider}"))


@app.route("/auth/disconnect/<provider>", methods=["POST"])
def auth_disconnect(provider: str):
    if provider not in truelayer.PROVIDERS:
        abort(404)
    db = get_db()
    truelayer.disconnect(db, provider)
    return redirect(url_for("budget", flash=f"disconnected_{provider}"))


# ---------------------------------------------------------------------------
# Budget page
# ---------------------------------------------------------------------------


@app.route("/budget")
def budget():
    db = get_db()
    status = truelayer.get_connection_status(db)

    today = date.today()
    view = request.args.get("view", "month")
    projection = request.args.get("projection", "") == "on"
    active_provider = request.args.get("provider", "all")

    if view == "year":
        since = datetime(today.year, 1, 1, tzinfo=timezone.utc)
    else:
        since = datetime(today.year, today.month, 1, tzinfo=timezone.utc)

    connected_providers = [p for p in truelayer.PROVIDERS if status[p] == "connected"]

    provider_transactions: dict[str, list[dict]] = {}
    all_transactions: list[dict] = []
    for provider in connected_providers:
        txns = truelayer.get_transactions(db, provider, since=since)
        provider_transactions[provider] = txns
        all_transactions.extend(txns)

    def _build(txns: list[dict], cat_limits=None) -> tuple[dict, dict | None]:
        if view == "year":
            return budget_module.build_yearly_charts(
                txns, today.year, projection, cat_limits
            ), None
        return (
            budget_module.build_monthly_charts(
                txns, today.year, today.month, projection, cat_limits
            ),
            budget_module.monthly_summary(txns, today.year, today.month, cat_limits),
        )

    views: dict[str, dict] = {"all": {}}
    views["all"]["charts"], views["all"]["summary"] = _build(all_transactions)
    for provider, txns in provider_transactions.items():
        c, s = _build(txns, PROVIDER_BUDGET_LIMITS.get(provider))
        views[provider] = {"charts": c, "summary": s}

    if active_provider not in views:
        active_provider = "all"

    charts = views[active_provider]["charts"]
    summary = views[active_provider]["summary"]
    flash = request.args.get("flash", "")

    return render_template(
        "budget.html",
        status=status,
        providers=truelayer.PROVIDERS,
        connected_providers=connected_providers,
        charts=charts,
        flash=flash,
        view=view,
        projection=projection,
        summary=summary,
        active_provider=active_provider,
    )


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------


@app.route("/debug")
def debug():
    return render_template("debug.html")
