"""Budget logic: category mapping and Plotly chart builders."""

import calendar
import json
from calendar import monthrange
from datetime import date, datetime
from typing import Any

import plotly
import plotly.graph_objects as go

from good_start_habits.config import (
    BUDGET_LIMITS,
    CATEGORY_GROUPS,
    CATEGORY_MAP,
    DESCRIPTION_PATTERNS,
    SAVINGS_ACCOUNTS,
)

_CATEGORY_COLOURS = [
    "#EF820D",
    "#0d7aef",
    "#2ecc71",
    "#e74c3c",
    "#9b59b6",
    "#1abc9c",
    "#f39c12",
    "#3498db",
    "#e67e22",
]

_BURN_COLOURS = [
    "#FF6B6B",  # coral
    "#FFA500",  # orange
    "#FFD700",  # gold
    "#4ECDC4",  # teal
    "#45B7D1",  # sky blue
    "#96CEB4",  # mint
    "#DDA0DD",  # plum
    "#F7DC6F",  # yellow
    "#BB8FCE",  # lavender
    "#98D8C8",  # seafoam
]

_overrides: dict[str, str] = {}

ALL_CATEGORY_NAMES: list[str] = [c for cats in CATEGORY_GROUPS.values() for c in cats]


def load_overrides(con: Any) -> None:
    global _overrides
    rows = con.execute(
        "SELECT description_lower, category FROM category_overrides"
    ).fetchall()
    _overrides = {r[0]: r[1] for r in rows}


_CHART_LAYOUT = {
    "paper_bgcolor": "#FFFFFF",
    "plot_bgcolor": "#FFFFFF",
    "font": {"family": "VT323, monospace", "color": "#888888", "size": 13},
    "margin": {"l": 55, "r": 20, "t": 16, "b": 65},
    "xaxis": {
        "gridcolor": "#F0F0F0",
        "tickcolor": "#DDDDDD",
        "linecolor": "#CCCCCC",
        "tickfont": {"size": 13, "color": "#888888"},
    },
    "yaxis": {
        "gridcolor": "#F0F0F0",
        "tickcolor": "#DDDDDD",
        "linecolor": "#CCCCCC",
        "zeroline": True,
        "zerolinecolor": "#FF1493",
        "zerolinewidth": 2,
        "tickfont": {"size": 13, "color": "#888888"},
        "tickprefix": "£",
        "rangemode": "tozero",
    },
    "legend": {
        "orientation": "h",
        "y": -0.24,
        "font": {"size": 13},
        "bgcolor": "rgba(0,0,0,0)",
    },
    "hovermode": "x unified",
    "hoverlabel": {"bgcolor": "#111111", "font_color": "#FFE600", "font_size": 14},
}


def _clean_desc(raw: str) -> str:
    s = raw.strip()
    if s == s.upper() and len(s) > 3:
        return s.title()
    return s


def map_category(
    classification: Any,
    description: str = "",
    amount: float = 0.0,
    provider: str = "",
) -> str | None:
    """Return personal category string, or None for transfers/income to exclude.

    amount should be the absolute spend value (positive).
    provider is the source bank (monzo, nationwide, amex).
    """
    desc = description.lower()

    for pattern, cat_override in _overrides.items():
        if pattern in desc:
            return cat_override

    # Amrit PayPal conditional: rent-adjacent payment if £80–£115, else misc
    if "amrit" in desc and "paypal" in desc:
        return "Bills & Utilities" if 80.0 <= amount <= 115.0 else "Other"

    cat: str | None = None
    matched = False
    if isinstance(classification, list) and classification:
        top = classification[0]
        sub = classification[1] if len(classification) > 1 else ""
        full_key = f"{top}|{sub}" if sub else top
        if full_key in CATEGORY_MAP:
            cat = CATEGORY_MAP[full_key]
            matched = True
        elif top in CATEGORY_MAP:
            cat = CATEGORY_MAP[top]
            matched = True

    if not matched:
        for pattern, category in DESCRIPTION_PATTERNS:
            if pattern in desc:
                cat = category
                matched = True
                break
    elif cat is None:
        # Classification said "transfer/income" but check if a specific description
        # pattern gives a positive match (e.g. "ashtons" → Rent overrides a Transfer
        # classification for a standing-order rent payment).
        for pattern, category in DESCRIPTION_PATTERNS:
            if pattern in desc and category is not None:
                cat = category
                break

    if not matched:
        cat = "Other"

    if cat is None:
        return None

    # Provider-aware food split: Amex food → Groceries (big shop)
    if provider == "amex" and cat == "Food & Coffee":
        cat = "Groceries"

    return cat


def _spending(transactions: list[dict]) -> list[dict]:
    """Outgoing transactions only, with transfers/income excluded."""
    result = []
    for t in transactions:
        if t.get("amount", 0) >= 0:
            continue
        if (
            map_category(
                t.get("transaction_classification", []),
                t.get("description", ""),
                abs(t.get("amount", 0.0)),
                t.get("_provider", ""),
            )
            is None
        ):
            continue
        result.append(t)
    return result


def _savings_by_account(
    transactions: list[dict], year: int, month: int
) -> dict[str, dict[int, float]]:
    """Map savings transactions in month to {account_name: {day: amount}}."""
    month_prefix = f"{year:04d}-{month:02d}"
    result: dict[str, dict[int, float]] = {}
    for t in transactions:
        if t.get("amount", 0) >= 0:
            continue
        if t.get("timestamp", "")[:7] != month_prefix:
            continue
        desc = t.get("description", "").lower()
        matched: str | None = None
        for acc in SAVINGS_ACCOUNTS:
            if any(p in desc for p in acc["patterns"]):
                matched = acc["name"]
                break
        if matched is None:
            if "bonds" in desc:
                matched = "Premium Bonds"
            else:
                continue
        try:
            day = int(t["timestamp"][8:10])
        except (KeyError, ValueError, IndexError):
            day = 1
        amt = abs(t["amount"])
        result.setdefault(matched, {})
        result[matched][day] = result[matched].get(day, 0.0) + amt
    return result


def _savings_totals(
    transactions: list[dict], year: int, month: int
) -> tuple[float, dict[int, float]]:
    """Return (total_saved, {day: amount}) — delegates to _savings_by_account."""
    by_account = _savings_by_account(transactions, year, month)
    total = 0.0
    daily: dict[int, float] = {}
    for acc_daily in by_account.values():
        for d, amt in acc_daily.items():
            total += amt
            daily[d] = daily.get(d, 0.0) + amt
    return round(total, 2), daily


def _add_burn_rate_monthly(
    fig: go.Figure,
    cat_day: dict[str, dict[int, float]],
    days_axis: list[int],
    days_in_month: int,
    days_so_far: int,
    is_current_month: bool,
    projection: bool,
    cat_limits: dict[str, float],
) -> None:
    """Add cumulative-spend burn-rate traces to fig (monthly view)."""
    for idx, (cat, day_totals) in enumerate(sorted(cat_day.items())):
        colour = _BURN_COLOURS[idx % len(_BURN_COLOURS)]
        budget_for_cat = cat_limits.get(cat, 0.0)
        running_spend = 0.0
        cumulative: list[float] = []
        for d in days_axis:
            running_spend += day_totals.get(d, 0.0)
            cumulative.append(round(running_spend, 2))

        fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=cumulative,
                name=cat,
                mode="lines",
                line={
                    "color": colour,
                    "width": 2.5,
                    "shape": "spline",
                    "smoothing": 0.7,
                },
                hovertemplate=f"<b>{cat}</b>: £%{{y:.0f}}<extra></extra>",
            )
        )

        if budget_for_cat > 0:
            fig.add_shape(
                type="line",
                x0=1,
                x1=days_in_month,
                y0=budget_for_cat,
                y1=budget_for_cat,
                line={"color": colour, "width": 1, "dash": "dot"},
                opacity=0.35,
            )

        if (
            projection
            and is_current_month
            and 0 < days_so_far < days_in_month
            and running_spend > 0
        ):
            projected_end = round(running_spend * days_in_month / days_so_far, 2)
            fig.add_trace(
                go.Scatter(
                    x=[days_so_far, days_in_month],
                    y=[running_spend, projected_end],
                    mode="lines",
                    line={"color": colour, "dash": "dash", "width": 1.5},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )


def build_savings_chart(
    transactions: list[dict],
    year: int,
    month: int,
    baselines: dict[str, float],
) -> str | None:
    """Multi-account savings chart: per-account lines + TOTAL, with projections."""
    today = date.today()
    days_in_month = monthrange(year, month)[1]
    is_current_month = today.year == year and today.month == month
    days_so_far = today.day if is_current_month else days_in_month
    days_axis = list(range(1, days_so_far + 1))

    account_daily = _savings_by_account(transactions, year, month)
    acc_cfg_map = {a["name"]: a for a in SAVINGS_ACCOUNTS}

    # Accounts to show: have transactions OR a non-zero baseline
    active: list[str] = []
    seen: set[str] = set()
    for acc in SAVINGS_ACCOUNTS:
        n = acc["name"]
        if n not in seen and (n in account_daily or baselines.get(n, 0.0) > 0):
            active.append(n)
            seen.add(n)
    for n in account_daily:
        if n not in seen:
            active.append(n)
            seen.add(n)

    if not active:
        return None

    fig = go.Figure()
    total_daily: dict[int, float] = {}

    for acc_name in active:
        cfg = acc_cfg_map.get(acc_name, {})
        colour = cfg.get("colour", "#AAAAAA")
        baseline = baselines.get(acc_name, 0.0)
        daily = account_daily.get(acc_name, {})

        running = baseline
        cumulative: list[float] = []
        for d in days_axis:
            amt = daily.get(d, 0.0)
            running += amt
            cumulative.append(round(running, 2))
            total_daily[d] = total_daily.get(d, 0.0) + amt

        fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=cumulative,
                name=acc_name,
                mode="lines",
                line={"color": colour, "width": 2, "shape": "spline", "smoothing": 0.5},
                hovertemplate=f"<b>{acc_name}</b>: £%{{y:,.0f}}<extra></extra>",
            )
        )

        if (
            is_current_month
            and 0 < days_so_far < days_in_month
            and sum(daily.values()) > 0
        ):
            monthly_contrib = sum(daily.values())
            remaining_days = days_in_month - days_so_far
            daily_rate = monthly_contrib / days_so_far if days_so_far > 0 else 0.0
            bonus = 0.0
            if "annual_bonus_rate" in cfg:
                annual_pace = monthly_contrib * 12
                eligible = min(annual_pace, cfg.get("annual_bonus_cap", 0.0))
                bonus = eligible * cfg["annual_bonus_rate"] / 12
            elif "annual_return_rate" in cfg:
                bonus = running * cfg["annual_return_rate"] / 12
            elif "annual_prize_rate" in cfg:
                bonus = running * cfg["annual_prize_rate"] / 12
            proj_end = round(running + daily_rate * remaining_days + bonus, 2)
            fig.add_trace(
                go.Scatter(
                    x=[days_so_far, days_in_month],
                    y=[running, proj_end],
                    mode="lines",
                    line={"color": colour, "dash": "dot", "width": 1.5},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # TOTAL line (only meaningful when > 1 account)
    total_baseline = sum(baselines.get(n, 0.0) for n in active)
    t_run = total_baseline
    total_cum: list[float] = []
    for d in days_axis:
        t_run += total_daily.get(d, 0.0)
        total_cum.append(round(t_run, 2))

    if len(active) > 1:
        fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=total_cum,
                name="TOTAL",
                mode="lines",
                line={
                    "color": "#FFE600",
                    "width": 4,
                    "shape": "spline",
                    "smoothing": 0.5,
                },
                hovertemplate="<b>TOTAL</b>: £%{y:,.0f}<extra></extra>",
            )
        )
        if is_current_month and 0 < days_so_far < days_in_month:
            total_monthly = sum(total_daily.values())
            dr = total_monthly / days_so_far if days_so_far > 0 else 0.0
            proj_total = round(t_run + dr * (days_in_month - days_so_far), 2)
            fig.add_trace(
                go.Scatter(
                    x=[days_so_far, days_in_month],
                    y=[t_run, proj_total],
                    mode="lines",
                    line={"color": "#FFE600", "dash": "dot", "width": 2.5},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "VT323, monospace", "color": "#888888", "size": 13},
        margin={"l": 70, "r": 20, "t": 16, "b": 44},
        xaxis={
            "title": {"text": "DAY"},
            "range": [1, days_in_month],
            "gridcolor": "#F0F0F0",
            "tickcolor": "#DDDDDD",
            "linecolor": "#CCCCCC",
        },
        yaxis={
            "title": {"text": "£ BALANCE"},
            "gridcolor": "#F0F0F0",
            "tickcolor": "#DDDDDD",
            "linecolor": "#CCCCCC",
            "tickprefix": "£",
            "tickformat": ",d",
            "rangemode": "tozero",
        },
        legend={
            "orientation": "v",
            "x": 0.02,
            "y": 0.98,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 12},
            "bgcolor": "rgba(255,255,255,0.88)",
            "bordercolor": "#DDDDDD",
            "borderwidth": 1,
        },
        hovermode="x unified",
        hoverlabel={"bgcolor": "#111111", "font_color": "#FFE600", "font_size": 14},
        showlegend=True,
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def build_wrong_card_chart(
    transactions: list[dict],
    year: int,
    month: int,
    cat_names: list[str],
) -> str | None:
    """Multi-line burn chart for categories spent on the wrong card."""
    today = date.today()
    days_in_month = monthrange(year, month)[1]
    is_current_month = today.year == year and today.month == month
    days_so_far = today.day if is_current_month else days_in_month
    days_axis = list(range(1, days_so_far + 1))

    month_prefix = f"{year:04d}-{month:02d}"
    cat_day: dict[str, dict[int, float]] = {}
    for t in transactions:
        if t.get("amount", 0) >= 0:
            continue
        if t.get("timestamp", "")[:7] != month_prefix:
            continue
        cat = map_category(
            t.get("transaction_classification", []),
            t.get("description", ""),
            abs(t.get("amount", 0.0)),
            t.get("_provider", ""),
        )
        if cat not in cat_names:
            continue
        try:
            day = int(t["timestamp"][8:10])
        except (KeyError, ValueError, IndexError):
            continue
        cat_day.setdefault(cat, {})
        cat_day[cat][day] = cat_day[cat].get(day, 0.0) + abs(t["amount"])

    if not cat_day:
        return None

    fig = go.Figure()
    for idx, cat in enumerate(sorted(cat_day.keys())):
        colour = _BURN_COLOURS[idx % len(_BURN_COLOURS)]
        day_totals = cat_day[cat]
        running = 0.0
        cumulative: list[float] = []
        for d in days_axis:
            running += day_totals.get(d, 0.0)
            cumulative.append(round(running, 2))
        fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=cumulative,
                name=cat,
                mode="lines",
                line={"color": colour, "width": 2, "shape": "spline", "smoothing": 0.5},
                hovertemplate=f"<b>{cat}</b>: £%{{y:,.0f}}<extra></extra>",
            )
        )

    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "VT323, monospace", "color": "#888888", "size": 13},
        margin={"l": 55, "r": 20, "t": 16, "b": 65},
        xaxis={
            "title": {"text": "DAY"},
            "range": [1, days_in_month],
            "gridcolor": "#F0F0F0",
            "tickcolor": "#DDDDDD",
            "linecolor": "#CCCCCC",
        },
        yaxis={
            "title": {"text": "£ SPENT"},
            "gridcolor": "#F0F0F0",
            "tickcolor": "#DDDDDD",
            "linecolor": "#CCCCCC",
            "zeroline": True,
            "zerolinecolor": "#FF6B00",
            "zerolinewidth": 2,
            "tickprefix": "£",
            "rangemode": "tozero",
        },
        legend={
            "orientation": "h",
            "y": -0.24,
            "font": {"size": 13},
            "bgcolor": "rgba(0,0,0,0)",
        },
        hovermode="x unified",
        hoverlabel={"bgcolor": "#111111", "font_color": "#FFE600", "font_size": 14},
        showlegend=True,
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def build_monthly_charts(
    transactions: list[dict],
    year: int,
    month: int,
    projection: bool,
    cat_limits: dict[str, float] | None = None,
    baselines: dict[str, float] | None = None,
) -> dict[str, str]:
    if cat_limits is None:
        cat_limits = BUDGET_LIMITS
    today = date.today()
    days_in_month = monthrange(year, month)[1]
    is_current_month = today.year == year and today.month == month
    days_so_far = today.day if is_current_month else days_in_month

    month_prefix = f"{year:04d}-{month:02d}"
    spending = [
        t for t in _spending(transactions) if t.get("timestamp", "")[:7] == month_prefix
    ]
    total_savings, savings_daily = _savings_totals(transactions, year, month)

    cat_day: dict[str, dict[int, float]] = {}
    for txn in spending:
        try:
            day = int(txn["timestamp"][8:10])
        except (KeyError, ValueError, IndexError):
            continue
        cat = map_category(
            txn.get("transaction_classification", []),
            txn.get("description", ""),
            abs(txn.get("amount", 0.0)),
            txn.get("_provider", ""),
        )
        if cat is None:
            continue
        cat_day.setdefault(cat, {})
        cat_day[cat][day] = cat_day[cat].get(day, 0.0) + abs(txn["amount"])

    if not cat_day:
        return {}

    charts: dict[str, str] = {}
    days_axis = list(range(1, days_so_far + 1))

    # ── Burn rate (primary) ─────────────────────────────────────────────────
    burn_fig = go.Figure()
    _add_burn_rate_monthly(
        burn_fig,
        cat_day,
        days_axis,
        days_in_month,
        days_so_far,
        is_current_month,
        projection,
        cat_limits,
    )
    if savings_daily:
        sav_running = 0.0
        sav_cumulative: list[float] = []
        for d in days_axis:
            sav_running += savings_daily.get(d, 0.0)
            sav_cumulative.append(round(sav_running, 2))
        burn_fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=sav_cumulative,
                name="Savings",
                mode="lines",
                line={"color": "#00C851", "width": 2.5, "dash": "dot"},
                hovertemplate="<b>Savings</b>: £%{y:.0f}<extra></extra>",
            )
        )
        if (
            projection
            and is_current_month
            and 0 < days_so_far < days_in_month
            and sav_running > 0
        ):
            projected_sav = round(sav_running * days_in_month / days_so_far, 2)
            burn_fig.add_trace(
                go.Scatter(
                    x=[days_so_far, days_in_month],
                    y=[sav_running, projected_sav],
                    mode="lines",
                    line={"color": "#00C851", "dash": "dash", "width": 1.5},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    burn_fig.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Day",
        yaxis_title="£ spent",
    )
    burn_fig.update_xaxes(range=[1, days_in_month])
    charts["burn_rate"] = json.dumps(burn_fig, cls=plotly.utils.PlotlyJSONEncoder)

    # ── Remaining budget per category (kept for year-compat) ────────────────
    fig = go.Figure()
    fig.add_shape(
        type="line",
        x0=1,
        x1=days_in_month,
        y0=0,
        y1=0,
        line={"color": "#999", "width": 1},
        opacity=0.5,
    )
    for idx, (cat, day_totals) in enumerate(sorted(cat_day.items())):
        colour = _CATEGORY_COLOURS[idx % len(_CATEGORY_COLOURS)]
        budget_for_cat = cat_limits.get(cat, 0.0)
        running_spend = 0.0
        remaining = []
        for d in days_axis:
            running_spend += day_totals.get(d, 0.0)
            remaining.append(round(budget_for_cat - running_spend, 2))
        fig.add_trace(
            go.Scatter(
                x=days_axis,
                y=remaining,
                name=cat,
                mode="lines",
                line={"color": colour, "width": 2},
            )
        )
        if projection and is_current_month and 0 < days_so_far < days_in_month:
            projected_remaining = round(
                budget_for_cat - (running_spend * days_in_month / days_so_far), 2
            )
            fig.add_trace(
                go.Scatter(
                    x=[days_so_far, days_in_month],
                    y=[remaining[-1], projected_remaining],
                    mode="lines",
                    line={"color": colour, "dash": "dash", "width": 1},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig.update_layout(
        paper_bgcolor="#f8f5f0",
        plot_bgcolor="#f8f5f0",
        font={"family": "Georgia, serif", "color": "#1a1a1a"},
        title=f"Remaining budget — {datetime(year, month, 1).strftime('%B %Y')}",
        xaxis_title="Day of month",
        yaxis_title="£ remaining",
        xaxis={"range": [1, days_in_month]},
        margin={"l": 60, "r": 20, "t": 50, "b": 80},
        legend={"orientation": "h", "y": -0.25},
    )
    charts["cumulative"] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # ── Budget vs actual bar ─────────────────────────────────────────────────
    all_cats = sorted(set(cat_day) | set(cat_limits))
    actuals = [round(sum(cat_day.get(c, {}).values()), 2) for c in all_cats]
    lim_vals = [cat_limits.get(c, 0.0) for c in all_cats]
    pairs = [
        (c, act, lim)
        for c, act, lim in zip(all_cats, actuals, lim_vals)
        if act > 0 or lim > 0
    ]
    if pairs:
        bar_cats = [p[0] for p in pairs]
        bar_acts = [p[1] for p in pairs]
        bar_lims = [p[2] for p in pairs]
        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                x=bar_cats,
                y=bar_lims,
                name="Budget",
                marker_color="rgba(200,200,200,0.7)",
            )
        )
        bar_fig.add_trace(
            go.Bar(x=bar_cats, y=bar_acts, name="Spent", marker_color="#EF820D")
        )
        bar_fig.update_layout(
            paper_bgcolor="#f8f5f0",
            plot_bgcolor="#f8f5f0",
            font={"family": "Georgia, serif", "color": "#1a1a1a"},
            title="Budget vs actual",
            barmode="overlay",
            xaxis={"tickangle": -35},
            margin={"l": 60, "r": 20, "t": 50, "b": 120},
            legend={"orientation": "h", "y": -0.45},
        )
        charts["vs_budget"] = json.dumps(bar_fig, cls=plotly.utils.PlotlyJSONEncoder)

    # ── Per-category JS data ─────────────────────────────────────────────────
    all_cats_js = sorted(set(cat_day) | set(cat_limits))
    per_cat_list = []
    for cat in all_cats_js:
        dtotals = cat_day.get(cat, {})
        budget_for_cat = cat_limits.get(cat, 0.0)
        running_spend = 0.0
        cat_remaining: list[float] = []
        for d in days_axis:
            running_spend += dtotals.get(d, 0.0)
            cat_remaining.append(round(budget_for_cat - running_spend, 2))
        per_cat_list.append(
            {
                "name": cat,
                "x": days_axis,
                "y": cat_remaining,
                "proj": None,
                "days_in_month": days_in_month,
            }
        )

    total_baseline_val = sum((baselines or {}).values())
    if total_savings > 0 or total_baseline_val > 0:
        sav_chart = build_savings_chart(transactions, year, month, baselines or {})
        if sav_chart:
            charts["savings"] = sav_chart
        # Total balance per day (baselines + monthly contributions) for badge
        sav_total_run = total_baseline_val
        sav_total_y: list[float] = []
        for d in days_axis:
            sav_total_run += savings_daily.get(d, 0.0)
            sav_total_y.append(round(sav_total_run, 2))
        per_cat_list.append(
            {
                "name": "Savings",
                "x": days_axis,
                "y": sav_total_y,
                "proj": None,
                "days_in_month": days_in_month,
                "is_savings": True,
            }
        )

    charts["per_category"] = json.dumps(per_cat_list)

    return charts


def build_yearly_charts(
    transactions: list[dict],
    year: int,
    projection: bool,
    cat_limits: dict[str, float] | None = None,
) -> dict[str, str]:
    if cat_limits is None:
        cat_limits = BUDGET_LIMITS
    today = date.today()
    is_current_year = today.year == year
    months_so_far = today.month if is_current_year else 12

    spending = [
        t for t in _spending(transactions) if t.get("timestamp", "")[:4] == str(year)
    ]

    cat_month: dict[str, dict[int, float]] = {}
    for txn in spending:
        try:
            m = int(txn["timestamp"][5:7])
        except (KeyError, ValueError, IndexError):
            continue
        cat = map_category(
            txn.get("transaction_classification", []),
            txn.get("description", ""),
            abs(txn.get("amount", 0.0)),
            txn.get("_provider", ""),
        )
        if cat is None:
            continue
        cat_month.setdefault(cat, {})
        cat_month[cat][m] = cat_month[cat].get(m, 0.0) + abs(txn["amount"])

    if not cat_month:
        return {}

    months_axis = list(range(1, months_so_far + 1))
    month_labels = [calendar.month_abbr[m] for m in months_axis]
    all_month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    charts: dict[str, str] = {}

    # ── Yearly burn rate (primary) ───────────────────────────────────────────
    burn_fig = go.Figure()
    for idx, (cat, month_totals) in enumerate(sorted(cat_month.items())):
        colour = _BURN_COLOURS[idx % len(_BURN_COLOURS)]
        annual_budget = cat_limits.get(cat, 0.0) * 12
        running_spend = 0.0
        cumulative: list[float] = []
        for m in months_axis:
            running_spend += month_totals.get(m, 0.0)
            cumulative.append(round(running_spend, 2))

        burn_fig.add_trace(
            go.Scatter(
                x=month_labels,
                y=cumulative,
                name=cat,
                mode="lines+markers",
                line={"color": colour, "width": 2.5},
                marker={"size": 5},
                hovertemplate=f"<b>{cat}</b>: £%{{y:.0f}}<extra></extra>",
            )
        )
        if annual_budget > 0:
            burn_fig.add_shape(
                type="line",
                x0=month_labels[0],
                x1=all_month_labels[11],
                y0=annual_budget,
                y1=annual_budget,
                line={"color": colour, "width": 1, "dash": "dot"},
                opacity=0.35,
            )
        if (
            projection
            and is_current_year
            and 0 < months_so_far < 12
            and running_spend > 0
        ):
            projected_end = round(running_spend * 12 / months_so_far, 2)
            burn_fig.add_trace(
                go.Scatter(
                    x=[month_labels[-1], all_month_labels[11]],
                    y=[running_spend, projected_end],
                    mode="lines",
                    line={"color": colour, "dash": "dash", "width": 1.5},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    burn_fig.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Month",
        yaxis_title="£ spent",
    )
    charts["burn_rate"] = json.dumps(burn_fig, cls=plotly.utils.PlotlyJSONEncoder)

    # ── Remaining budget per category ────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=all_month_labels,
            y=[0] * 12,
            mode="lines",
            line={"color": "#999", "width": 1},
            opacity=0.5,
            showlegend=False,
            hoverinfo="skip",
        )
    )
    for idx, (cat, month_totals) in enumerate(sorted(cat_month.items())):
        colour = _CATEGORY_COLOURS[idx % len(_CATEGORY_COLOURS)]
        annual_budget = cat_limits.get(cat, 0.0) * 12
        running_spend = 0.0
        remaining = []
        for m in months_axis:
            running_spend += month_totals.get(m, 0.0)
            remaining.append(round(annual_budget - running_spend, 2))
        fig.add_trace(
            go.Scatter(
                x=month_labels,
                y=remaining,
                name=cat,
                mode="lines+markers",
                line={"color": colour, "width": 2},
                marker={"size": 5},
            )
        )
        if projection and is_current_year and 0 < months_so_far < 12:
            projected_remaining = round(
                annual_budget - (running_spend * 12 / months_so_far), 2
            )
            fig.add_trace(
                go.Scatter(
                    x=[month_labels[-1], all_month_labels[11]],
                    y=[remaining[-1], projected_remaining],
                    mode="lines",
                    line={"color": colour, "dash": "dash", "width": 1},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig.update_layout(
        paper_bgcolor="#f8f5f0",
        plot_bgcolor="#f8f5f0",
        font={"family": "Georgia, serif", "color": "#1a1a1a"},
        title=f"Remaining budget — {year}",
        xaxis_title="Month",
        yaxis_title="£ remaining",
        margin={"l": 60, "r": 20, "t": 50, "b": 80},
        legend={"orientation": "h", "y": -0.25},
    )
    charts["cumulative"] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # ── Budget vs actual bar ─────────────────────────────────────────────────
    all_cats = sorted(set(cat_month) | set(cat_limits))
    actuals = [round(sum(cat_month.get(c, {}).values()), 2) for c in all_cats]
    annual_limits = [cat_limits.get(c, 0.0) * 12 for c in all_cats]
    pairs = [
        (c, act, lim)
        for c, act, lim in zip(all_cats, actuals, annual_limits)
        if act > 0 or lim > 0
    ]
    if pairs:
        cats, act_vals, lim_vals = zip(*pairs)
        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                x=list(cats),
                y=list(lim_vals),
                name="Annual budget",
                marker_color="rgba(200,200,200,0.7)",
            )
        )
        bar_fig.add_trace(
            go.Bar(x=list(cats), y=list(act_vals), name="Spent", marker_color="#EF820D")
        )
        bar_fig.update_layout(
            paper_bgcolor="#f8f5f0",
            plot_bgcolor="#f8f5f0",
            font={"family": "Georgia, serif", "color": "#1a1a1a"},
            title="Budget vs actual (year to date)",
            barmode="overlay",
            xaxis={"tickangle": -35},
            margin={"l": 60, "r": 20, "t": 50, "b": 120},
            legend={"orientation": "h", "y": -0.45},
        )
        charts["vs_budget"] = json.dumps(bar_fig, cls=plotly.utils.PlotlyJSONEncoder)

    return charts


def monthly_summary(
    transactions: list[dict],
    year: int,
    month: int,
    cat_limits: dict[str, float] | None = None,
    income: float | None = None,
) -> dict:
    """Return spending totals, savings, income-based balance, and grouped categories."""
    if cat_limits is None:
        cat_limits = BUDGET_LIMITS
    today = date.today()
    is_current_month = today.year == year and today.month == month
    days_in_month = monthrange(year, month)[1]
    days_so_far = today.day if is_current_month else days_in_month

    month_prefix = f"{year:04d}-{month:02d}"
    spending = [
        t for t in _spending(transactions) if t.get("timestamp", "")[:7] == month_prefix
    ]
    cat_totals: dict[str, float] = {}
    for txn in spending:
        cat = map_category(
            txn.get("transaction_classification", []),
            txn.get("description", ""),
            abs(txn.get("amount", 0.0)),
            txn.get("_provider", ""),
        )
        if cat is None:
            continue
        cat_totals[cat] = cat_totals.get(cat, 0.0) + abs(txn["amount"])

    total_spent = round(sum(cat_totals.values()), 2)
    total_budget = sum(cat_limits.values())
    total_savings, _ = _savings_totals(transactions, year, month)

    projected_savings: float | None = None
    if total_savings > 0 and is_current_month and days_so_far > 0:
        projected_savings = round(total_savings * days_in_month / days_so_far, 2)

    usable_balance: float | None = None
    if income is not None:
        usable_balance = round(income - total_spent, 2)

    all_cats = sorted(set(cat_totals) | set(cat_limits))
    categories: list[dict] = []
    for cat in all_cats:
        spent = round(cat_totals.get(cat, 0.0), 2)
        budget_limit = cat_limits.get(cat, 0.0)
        if spent > 0 or budget_limit > 0:
            categories.append(
                {
                    "name": cat,
                    "spent": spent,
                    "budget": budget_limit,
                    "remaining": round(budget_limit - spent, 2),
                    "pct_used": round(spent / budget_limit * 100, 1)
                    if budget_limit
                    else 0.0,
                }
            )

    categories.sort(key=lambda c: float(c["spent"]), reverse=True)

    cat_by_name = {c["name"]: c for c in categories}
    grouped_categories: dict[str, list[dict]] = {}
    for group, group_cats in CATEGORY_GROUPS.items():
        grouped_categories[group] = [
            cat_by_name[c] for c in group_cats if c in cat_by_name
        ]
    ungrouped = [
        c
        for c in categories
        if not any(c["name"] in g for g in CATEGORY_GROUPS.values())
    ]
    if ungrouped:
        grouped_categories["Other"] = ungrouped

    return {
        "total_spent": total_spent,
        "total_budget": total_budget,
        "pct_used": round(total_spent / total_budget * 100, 1) if total_budget else 0,
        "total_savings": total_savings,
        "projected_savings": projected_savings,
        "income": income,
        "usable_balance": usable_balance,
        "by_category": cat_totals,
        "categories": categories,
        "grouped_categories": grouped_categories,
    }


def get_recent_transactions(
    provider_transactions: dict[str, list[dict]],
    limit: int = 15,
    year: int | None = None,
    month: int | None = None,
) -> list[dict]:
    """Return the most recent spending transactions across providers, annotated."""
    month_prefix = f"{year:04d}-{month:02d}" if year and month else None
    annotated = []
    for provider, txns in provider_transactions.items():
        for t in txns:
            if t.get("amount", 0) >= 0:
                continue
            if month_prefix and t.get("timestamp", "")[:7] != month_prefix:
                continue
            cat = map_category(
                t.get("transaction_classification", []),
                t.get("description", ""),
                abs(t.get("amount", 0.0)),
                t.get("_provider", ""),
            )
            if cat is None:
                continue
            annotated.append(
                {
                    "description": _clean_desc(t.get("description", "Unknown")),
                    "amount": round(abs(t.get("amount", 0)), 2),
                    "date": t.get("timestamp", "")[:10],
                    "provider": provider,
                    "category": cat,
                }
            )
    annotated.sort(key=lambda x: x["date"], reverse=True)
    return annotated[:limit]


def get_all_transactions_by_category(
    provider_transactions: dict[str, list[dict]],
    year: int | None = None,
    month: int | None = None,
) -> dict[str, list[dict]]:
    """Return all spending transactions grouped by personal category, date descending."""
    month_prefix = f"{year:04d}-{month:02d}" if year and month else None
    by_cat: dict[str, list[dict]] = {}
    for provider, txns in provider_transactions.items():
        for t in txns:
            if t.get("amount", 0) >= 0:
                continue
            if month_prefix and t.get("timestamp", "")[:7] != month_prefix:
                continue
            cat = map_category(
                t.get("transaction_classification", []),
                t.get("description", ""),
                abs(t.get("amount", 0.0)),
                t.get("_provider", ""),
            )
            if cat is None:
                continue
            entry = {
                "description": _clean_desc(t.get("description", "Unknown")),
                "amount": round(abs(t.get("amount", 0)), 2),
                "date": t.get("timestamp", "")[:10],
                "provider": provider,
            }
            by_cat.setdefault(cat, []).append(entry)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: x["date"], reverse=True)
    return by_cat
