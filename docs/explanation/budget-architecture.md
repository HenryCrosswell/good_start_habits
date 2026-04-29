# Explanation: Budget and categorisation

---

## Data flow

```
TrueLayer API
    → get_transactions(provider, since)
    → list of raw transaction dicts
    → map_category() for each transaction
    → categorised transactions
    → build_monthly_charts() / build_yearly_charts()
    → Plotly JSON embedded in the page
```

TrueLayer returns transactions from the last N days. The app fetches separately per provider, then merges them for the "all" view.

---

## Two-pass categorisation

`budget.map_category()` assigns a personal category to each transaction using two sources of truth in order of priority:

1. **Inline overrides** (`category_overrides` table) — checked first. If the transaction's lowercased description exactly matches a stored override, that category is used. These are set via the reclassify UI.

2. **`CATEGORY_MAP`** (`config.py`) — matched against TrueLayer's `transaction_classification` field. TrueLayer returns a list like `["Food", "Groceries"]`. The map supports two key formats:
   - `"Food|Groceries"` — matches if both top-level and sub-level match
   - `"Food"` — matches if the top-level matches

3. **`DESCRIPTION_PATTERNS`** (`config.py`) — if no classification match, scans the transaction description as a case-insensitive substring. First match wins.

4. **Fall back to `"Other"`** — if nothing matches.

5. **`None` = exclude** — a result of `None` from any step means the transaction is excluded from all spending totals. Used for transfers, income, and savings movements.

---

## Why two sources (classification + description)?

TrueLayer's classification is good but incomplete. Many merchants are unclassified or classified at too coarse a level (e.g. everything at a supermarket lands under `"Food"` rather than `"Food|Groceries"`). Description patterns fill the gaps: if you know "Tesco" always means a small shop rather than a big grocery run, you can override TrueLayer's classification.

---

## Sinking funds

Sinking fund categories (Haircut, Gigs, Steam Games, etc.) accumulate spend over a multi-month period, not month-to-month. Each has a list of reset months in `SINKING_FUND_RESETS`. When viewing the current month:

1. The app finds the most recent reset month at or before the current month (`_sf_period_start()`).
2. It fetches transactions back to that reset point, even if it's earlier than the selected month.
3. The chart shows cumulative spend since the last reset against the sinking fund limit.

This means a £45 haircut limit resets every 2 months — the chart starts at £0 in February, April, June, etc., and accumulates until the next reset.

---

## Provider limits and wrong-card detection

`PROVIDER_BUDGET_LIMITS` defines which categories belong on each card. When viewing a specific provider:

- Categories in that provider's limits are shown as expected spend.
- Categories with spend but no limit on that provider are flagged as WRONG CARD — money was spent on the wrong card.

WRONG CARD entries are shown in a separate section on the provider view and in a separate chart.

This is useful for tracking whether a recurring payment has silently moved to a different card (e.g. a subscription that should be on Nationwide ending up on Monzo).

---

## Why SQLite is sufficient

The budget data is not stored locally — every page load fetches fresh transactions from TrueLayer. SQLite only stores:
- OAuth tokens (small, per-provider)
- Category overrides (one row per merchant you've manually reclassified)
- Savings baselines (one row per account per month)
- Budget settings (one row per month)

This means the database is tiny and the app works fine without any migration tooling.

---

## Projection

When projection is on, the app extrapolates from the current day's cumulative spend to the end of the period using a simple linear rate: `current_spend / days_elapsed * total_days_in_period`. This is shown as a dashed line on the chart. It is only meaningful after the first few days of the month.
