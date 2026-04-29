"""Flask app — routes and startup."""

import atexit
import logging
import os
import sqlite3
from datetime import date, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from good_start_habits import budget as budget_module  # noqa: E402
from good_start_habits import truelayer  # noqa: E402
from good_start_habits.config import (
    CATEGORY_GROUPS,
    DWELL_TIME,
    PROVIDER_BUDGET_LIMITS,
    ROTATION_INTERVAL,
)  # noqa: E402
from good_start_habits.config import SAVINGS_ACCOUNTS  # noqa: E402
from good_start_habits.db import (  # noqa: E402
    get_budget_settings,
    get_db,
    get_savings_baselines,
    init_db,
    save_budget_settings,
    save_savings_baseline,
)
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
    budget_module.load_overrides(db)
    budget_module.load_sinking_fund(db)
    status = truelayer.get_connection_status(db)

    today = date.today()
    view = request.args.get("view", "month")
    projection = request.args.get("projection", "") == "on"
    active_provider = request.args.get("provider", "all")
    offset = max(-1, min(0, int(request.args.get("offset", "0"))))

    if offset == -1:
        if today.month == 1:
            disp_year, disp_month = today.year - 1, 12
        else:
            disp_year, disp_month = today.year, today.month - 1
    else:
        disp_year, disp_month = today.year, today.month

    settings = get_budget_settings(db, disp_year, disp_month)
    income = settings["base_income"] + settings["extra_income"]
    savings_baselines = get_savings_baselines(db, disp_year, disp_month)

    if view == "year":
        since = datetime(disp_year, 1, 1, tzinfo=timezone.utc)
    else:
        since = datetime(disp_year, disp_month, 1, tzinfo=timezone.utc)

    connected_providers = [p for p in truelayer.PROVIDERS if status[p] == "connected"]

    provider_transactions: dict[str, list[dict]] = {}
    all_transactions: list[dict] = []
    for provider in connected_providers:
        txns = truelayer.get_transactions(db, provider, since=since)
        provider_transactions[provider] = txns
        all_transactions.extend(txns)

    def _build(txns: list[dict], cat_limits=None, txn_income=None, sav_baselines=None):
        if view == "year":
            return budget_module.build_yearly_charts(
                txns, disp_year, projection, cat_limits
            ), None
        return (
            budget_module.build_monthly_charts(
                txns,
                disp_year,
                disp_month,
                projection,
                cat_limits,
                baselines=sav_baselines,
            ),
            budget_module.monthly_summary(
                txns, disp_year, disp_month, cat_limits, income=txn_income
            ),
        )

    views: dict[str, dict] = {"all": {}}
    views["all"]["charts"], views["all"]["summary"] = _build(
        all_transactions, txn_income=income, sav_baselines=savings_baselines
    )
    for provider, txns in provider_transactions.items():
        c, s = _build(txns, PROVIDER_BUDGET_LIMITS.get(provider))
        views[provider] = {"charts": c, "summary": s}

    if active_provider not in views:
        active_provider = "all"

    # Per-provider breakdown for left panel: expected vs error spend
    sf_cat_names = set(CATEGORY_GROUPS.get("Sinking Fund", []))
    provider_breakdowns: dict[str, dict] = {}
    for p in connected_providers:
        psummary = views[p].get("summary") if views.get(p) else None
        plimits = PROVIDER_BUDGET_LIMITS.get(p, {})
        pcats = (psummary or {}).get("categories", [])
        expected = [c for c in pcats if c["name"] in plimits]
        error_cats = [
            c
            for c in pcats
            if c["name"] not in plimits
            and c["spent"] > 0
            and c["name"] not in sf_cat_names
        ]
        provider_breakdowns[p] = {
            "categories": expected,
            "error_cats": error_cats,
            "error_total": round(sum(c["spent"] for c in error_cats), 2),
        }

    wrong_card_charts: dict[str, str] = {}
    if view == "month":
        for p in connected_providers:
            pdata = provider_breakdowns[p]
            error_names = [c["name"] for c in pdata["error_cats"]]
            if error_names:
                wc = budget_module.build_wrong_card_chart(
                    provider_transactions[p], disp_year, disp_month, error_names
                )
                if wc:
                    wrong_card_charts[p] = wc

    charts = views[active_provider]["charts"]
    summary = views[active_provider]["summary"]
    flash = request.args.get("flash", "")

    if active_provider == "all":
        recent_txn_source = provider_transactions
    else:
        recent_txn_source = {
            active_provider: provider_transactions.get(active_provider, [])
        }
    txn_year = disp_year if view == "month" else None
    txn_month = disp_month if view == "month" else None
    recent_transactions = budget_module.get_recent_transactions(
        recent_txn_source, year=txn_year, month=txn_month
    )
    category_transactions = budget_module.get_all_transactions_by_category(
        recent_txn_source, year=txn_year, month=txn_month
    )

    import calendar as _cal

    display_month = f"{_cal.month_name[disp_month].upper()} {disp_year}"

    sf_order = CATEGORY_GROUPS.get("Sinking Fund", [])
    all_summary = views["all"].get("summary") or {}
    sinking_fund_cats = [
        c for c in (all_summary.get("categories") or []) if c["name"] in sf_cat_names
    ]
    sinking_fund_cats.sort(
        key=lambda c: sf_order.index(c["name"]) if c["name"] in sf_order else 999
    )

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
        recent_transactions=recent_transactions,
        category_transactions=category_transactions,
        offset=offset,
        display_month=display_month,
        disp_year=disp_year,
        disp_month=disp_month,
        settings=settings,
        dwell_time=DWELL_TIME,
        all_categories=budget_module.ALL_CATEGORY_NAMES,
        provider_breakdowns=provider_breakdowns,
        savings_accounts=[
            {
                "name": acc["name"],
                "baseline": savings_baselines.get(acc["name"], 0.0),
                "colour": acc["colour"],
            }
            for acc in SAVINGS_ACCOUNTS
        ],
        wrong_card_charts=wrong_card_charts,
        sinking_fund_cats=sinking_fund_cats,
    )


@app.route("/budget/settings", methods=["POST"])
def budget_settings_save():
    db = get_db()
    _today = date.today()
    year = int(request.form.get("year", _today.year))
    month = int(request.form.get("month", _today.month))
    try:
        base_income = float(request.form.get("base_income", 2440.0))
        extra_income = float(request.form.get("extra_income", 100.0))
    except ValueError:
        base_income, extra_income = 2440.0, 100.0
    notes = request.form.get("notes", "")
    save_budget_settings(db, year, month, base_income, extra_income, notes)
    offset = request.form.get("offset", "0")
    return redirect(
        url_for(
            "budget",
            view=request.form.get("view", "month"),
            provider=request.form.get("provider", "all"),
            offset=offset,
        )
    )


@app.route("/budget/reclassify", methods=["POST"])
def budget_reclassify():
    db = get_db()
    description = request.form.get("description", "").lower().strip()
    category = request.form.get("category", "").strip()
    if description and category:
        db.execute(
            "INSERT INTO category_overrides (description_lower, category)"
            " VALUES (?, ?) ON CONFLICT(description_lower) DO UPDATE SET"
            " category = excluded.category",
            (description, category),
        )
        db.commit()
    return redirect(
        url_for(
            "budget",
            view=request.form.get("view", "month"),
            provider=request.form.get("provider", "all"),
            offset=request.form.get("offset", "0"),
            flash="recategorized",
        )
    )


@app.route("/budget/sinking-fund", methods=["POST"])
def budget_sinking_fund():
    db = get_db()
    description = request.form.get("description", "").strip().lower()
    action = request.form.get("action", "add")
    if description:
        if action == "add":
            db.execute(
                "INSERT OR IGNORE INTO sinking_fund_overrides (description_lower) VALUES (?)",
                (description,),
            )
        else:
            db.execute(
                "DELETE FROM sinking_fund_overrides WHERE description_lower = ?",
                (description,),
            )
        db.commit()
        budget_module.load_sinking_fund(db)
    return redirect(
        url_for(
            "budget",
            view=request.form.get("view", "month"),
            provider=request.form.get("provider", "all"),
            offset=request.form.get("offset", "0"),
            flash="sf_updated",
        )
    )


# ---------------------------------------------------------------------------
# Savings baselines
# ---------------------------------------------------------------------------


@app.route("/budget/savings-baseline", methods=["POST"])
def budget_savings_baseline():
    db = get_db()
    _today = date.today()
    year = int(request.form.get("year", _today.year))
    month = int(request.form.get("month", _today.month))
    for acc in SAVINGS_ACCOUNTS:
        key = "baseline_" + acc["name"].replace(" ", "_").lower()
        try:
            balance = float(request.form.get(key, 0.0))
        except ValueError:
            balance = 0.0
        save_savings_baseline(db, acc["name"], year, month, balance)
    return redirect(
        url_for(
            "budget",
            view=request.form.get("view", "month"),
            provider=request.form.get("provider", "all"),
            offset=request.form.get("offset", "0"),
        )
    )


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------


@app.route("/debug")
def debug():
    return render_template("debug.html")


@app.route("/debug/transactions/<provider>")
def debug_transactions(provider: str):
    """Dump raw TrueLayer transaction descriptions and classifications."""
    from good_start_habits.budget import map_category

    db = get_db()
    txns = truelayer.get_transactions(db, provider)
    out = []
    for t in txns:
        classification = t.get("transaction_classification", [])
        description = t.get("description", "")
        amount = t.get("amount", 0)
        mapped = map_category(classification, description, abs(amount), provider)
        out.append(
            {
                "date": t.get("timestamp", "")[:10],
                "description": description,
                "classification": classification,
                "amount": amount,
                "mapped_category": mapped,
            }
        )
    out.sort(key=lambda x: x["date"], reverse=True)
    return jsonify(out)
