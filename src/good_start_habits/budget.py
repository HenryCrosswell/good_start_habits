"""Budget logic: category mapping and Plotly chart builders."""

import calendar
import json
from calendar import monthrange
from datetime import date, datetime
from typing import Any

import plotly
import plotly.graph_objects as go

from good_start_habits.config import BUDGET_LIMITS, CATEGORY_MAP

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


def map_category(classification: Any) -> str:
    if not isinstance(classification, list) or not classification:
        return "Other"
    top = classification[0]
    sub = classification[1] if len(classification) > 1 else ""
    full_key = f"{top}|{sub}" if sub else top
    return CATEGORY_MAP.get(full_key) or CATEGORY_MAP.get(top) or "Other"


def _outgoing(transactions: list[dict]) -> list[dict]:
    return [t for t in transactions if t.get("amount", 0) < 0]


def build_monthly_charts(
    transactions: list[dict],
    year: int,
    month: int,
    projection: bool,
) -> dict[str, str]:
    today = date.today()
    days_in_month = monthrange(year, month)[1]
    is_current_month = today.year == year and today.month == month
    days_so_far = today.day if is_current_month else days_in_month

    month_prefix = f"{year:04d}-{month:02d}"
    spending = [
        t for t in _outgoing(transactions) if t.get("timestamp", "")[:7] == month_prefix
    ]

    cat_day: dict[str, dict[int, float]] = {}
    for txn in spending:
        try:
            day = int(txn["timestamp"][8:10])
        except (KeyError, ValueError, IndexError):
            continue
        cat = map_category(txn.get("transaction_classification", []))
        cat_day.setdefault(cat, {})
        cat_day[cat][day] = cat_day[cat].get(day, 0.0) + abs(txn["amount"])

    if not cat_day:
        return {}

    charts: dict[str, str] = {}
    days_axis = list(range(1, days_so_far + 1))

    # ── Primary: remaining budget per category ──────────────────────────────
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
        budget_for_cat = BUDGET_LIMITS.get(cat, 0.0)
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

    # ── Secondary: budget vs actual ─────────────────────────────────────────
    all_cats = sorted(set(cat_day) | set(BUDGET_LIMITS))
    actuals = [round(sum(cat_day.get(c, {}).values()), 2) for c in all_cats]
    limits = [BUDGET_LIMITS.get(c, 0.0) for c in all_cats]
    pairs = [
        (c, act, lim)
        for c, act, lim in zip(all_cats, actuals, limits)
        if act > 0 or lim > 0
    ]

    if pairs:
        cats, act_vals, lim_vals = zip(*pairs)
        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                x=list(cats),
                y=list(lim_vals),
                name="Budget",
                marker_color="rgba(200,200,200,0.7)",
            )
        )
        bar_fig.add_trace(
            go.Bar(
                x=list(cats),
                y=list(act_vals),
                name="Spent",
                marker_color="#EF820D",
            )
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

    # ── Per-category data for the linked single-category JS chart ───────────
    all_cats_js = sorted(set(cat_day) | set(BUDGET_LIMITS))
    per_cat_list = []
    for cat in all_cats_js:
        dtotals = cat_day.get(cat, {})
        budget_for_cat = BUDGET_LIMITS.get(cat, 0.0)
        running_spend = 0.0
        cat_remaining: list[float] = []
        for d in days_axis:
            running_spend += dtotals.get(d, 0.0)
            cat_remaining.append(round(budget_for_cat - running_spend, 2))
        proj = None
        if (
            projection
            and is_current_month
            and 0 < days_so_far < days_in_month
            and running_spend > 0
        ):
            proj = {
                "x": [days_so_far, days_in_month],
                "y": [
                    cat_remaining[-1],
                    round(
                        budget_for_cat - running_spend * days_in_month / days_so_far, 2
                    ),
                ],
            }
        per_cat_list.append(
            {
                "name": cat,
                "x": days_axis,
                "y": cat_remaining,
                "proj": proj,
                "days_in_month": days_in_month,
            }
        )
    charts["per_category"] = json.dumps(per_cat_list)

    return charts


def build_yearly_charts(
    transactions: list[dict],
    year: int,
    projection: bool,
) -> dict[str, str]:
    today = date.today()
    is_current_year = today.year == year
    months_so_far = today.month if is_current_year else 12

    spending = [
        t for t in _outgoing(transactions) if t.get("timestamp", "")[:4] == str(year)
    ]

    cat_month: dict[str, dict[int, float]] = {}
    for txn in spending:
        try:
            m = int(txn["timestamp"][5:7])
        except (KeyError, ValueError, IndexError):
            continue
        cat = map_category(txn.get("transaction_classification", []))
        cat_month.setdefault(cat, {})
        cat_month[cat][m] = cat_month[cat].get(m, 0.0) + abs(txn["amount"])

    if not cat_month:
        return {}

    months_axis = list(range(1, months_so_far + 1))
    month_labels = [calendar.month_abbr[m] for m in months_axis]
    all_month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    charts: dict[str, str] = {}

    # ── Primary: remaining budget per category ──────────────────────────────
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
        annual_budget = BUDGET_LIMITS.get(cat, 0.0) * 12
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

    # ── Secondary: budget vs actual ─────────────────────────────────────────
    all_cats = sorted(set(cat_month) | set(BUDGET_LIMITS))
    actuals = [round(sum(cat_month.get(c, {}).values()), 2) for c in all_cats]
    annual_limits = [BUDGET_LIMITS.get(c, 0.0) * 12 for c in all_cats]
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
            go.Bar(
                x=list(cats),
                y=list(act_vals),
                name="Spent",
                marker_color="#EF820D",
            )
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


def monthly_summary(transactions: list[dict], year: int, month: int) -> dict:
    """Return total spent, total budget, and per-category actuals for the month."""
    month_prefix = f"{year:04d}-{month:02d}"
    spending = [
        t for t in _outgoing(transactions) if t.get("timestamp", "")[:7] == month_prefix
    ]
    cat_totals: dict[str, float] = {}
    for txn in spending:
        cat = map_category(txn.get("transaction_classification", []))
        cat_totals[cat] = cat_totals.get(cat, 0.0) + abs(txn["amount"])

    total_spent = round(sum(cat_totals.values()), 2)
    total_budget = sum(BUDGET_LIMITS.values())

    all_cats = sorted(set(cat_totals) | set(BUDGET_LIMITS))
    categories = []
    for cat in all_cats:
        spent = round(cat_totals.get(cat, 0.0), 2)
        budget_limit = BUDGET_LIMITS.get(cat, 0.0)
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

    return {
        "total_spent": total_spent,
        "total_budget": total_budget,
        "pct_used": round(total_spent / total_budget * 100, 1) if total_budget else 0,
        "by_category": cat_totals,
        "categories": categories,
    }
