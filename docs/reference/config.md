# Reference: config.py

All user-configurable values live in `src/good_start_habits/config.py`. Restart the app after any change.

---

## Habits

### `HABITS`

`list[str]` — The ordered list of habit names. Each name must also appear in `HABIT_ACTIVE_DAYS`. The order here determines the order they appear on the habits page.

### `HABIT_ACTIVE_DAYS`

`dict[str, list[str]]` — Maps each habit name to the days of the week it should appear. Days are full English names, capitalised: `"Monday"`, `"Tuesday"`, etc.

A habit not scheduled for today simply does not appear — it is not flagged or counted as missed.

---

## Active hours

### `ACTIVE_TIMES`

`dict[str, tuple[str, str]]` — Maps each day name to a `(start, end)` pair of 24-hour `HH:MM:SS` strings. Outside this window, the clock shows a quiet message and the rotation to the habits page stops.

---

## Rotation

### `ROTATION_INTERVAL`

`int` — Seconds before the clock auto-navigates to `/habits` during active hours. Currently randomised between 1800 and 7200 on each app start. Replace `randint(1800, 7200)` with a fixed value once you have decided on an interval.

### `DWELL_TIME`

`int` — Seconds the habits page stays visible before returning to the clock. Currently randomised between 300 and 600.

---

## Budget limits

### `BUDGET_LIMITS`

`dict[str, float]` — Monthly spending limits in pounds, per personal category. Used in the "all" (combined) view on the budget page.

### `PROVIDER_BUDGET_LIMITS`

`dict[str, dict[str, float]]` — Per-provider monthly limits. Used when viewing a specific bank's transactions. Keys are `"monzo"`, `"nationwide"`, `"amex"`. Only categories listed here appear as expected spend for that provider — anything else is flagged as WRONG CARD.

### `BUDGET_LIMITS` vs `PROVIDER_BUDGET_LIMITS`

These two dicts represent the same budget at different granularities. They are maintained independently and can drift. The correct model:

- `PROVIDER_BUDGET_LIMITS` is the source of truth for any category tied to a specific card.
- `BUDGET_LIMITS` (the "all" view) should be the sum of that category across all providers, plus limits for categories with no provider assignment.

Every time you change a provider limit, check whether the `BUDGET_LIMITS` entry needs updating.

---

## Transaction categorisation

### `CATEGORY_MAP`

`dict[str, str | None]` — Maps TrueLayer classification strings to personal category names. Keys with `|` match both top-level and sub-level (e.g. `"Food|Groceries"`). Keys without `|` match the top-level only. A value of `None` excludes the transaction from all totals.

### `DESCRIPTION_PATTERNS`

`list[tuple[str, str | None]]` — Fallback patterns for transactions TrueLayer can't classify. Matched case-insensitively as substrings against the transaction description. First match wins. `None` excludes the transaction.

---

## Sinking funds

### `CATEGORY_GROUPS`

`dict[str, list[str]]` — Groups categories for display purposes and for identifying sinking fund categories. The `"Sinking Fund"` key lists all sinking fund category names.

### `SINKING_FUND_RESETS`

`dict[str, list[int]]` — Maps each sinking fund category to the months when its accumulation period resets. Month numbers, e.g. `[1, 4, 7, 10]` = quarterly.

---

## Income

### `BASE_INCOME`

`float` — Default monthly salary. Used as the starting value in the income panel on the budget page.

### `DEFAULT_EXTRA_INCOME`

`float` — Default monthly contribution from a partner or other source. Added to `BASE_INCOME` to calculate total income. This value should be updated in the settings panel each month if it varies.

---

## Savings accounts

### `SAVINGS_ACCOUNTS`

`list[dict]` — Defines the savings accounts shown on the budget page. Each entry has:

| Key | Type | Description |
|---|---|---|
| `name` | `str` | Display name |
| `patterns` | `list[str]` | Substrings matched against transaction descriptions to identify transfers to this account |
| `colour` | `str` | Hex colour for the chart |
| `annual_return_rate` | `float` | Expected annual return rate (used for projection) |
| `default_balance` | `float` | Balance shown before you enter a monthly baseline |

### `SAVINGS_PATTERNS`

`list[str]` — Flattened list of all patterns from `SAVINGS_ACCOUNTS`, used to exclude savings transfers from spending totals.
