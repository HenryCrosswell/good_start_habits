# Reference: Routes

All routes are defined in `src/good_start_habits/app.py`.

---

## Clock / standby

### `GET /`

Renders the standby clock page. Checks whether the current time falls within today's active hours (`config.ACTIVE_TIMES`). If active, passes `rotation_interval` to the template so the JavaScript timer can navigate to `/habits` automatically.

---

## Habits

### `GET /habits`

Renders the habit checklist. Calls `daily_maintenance()` on every load — this resets `done_today` at the start of a new day and zeroes streaks after 3+ days of inactivity.

Only habits scheduled for today (per `HABIT_ACTIVE_DAYS`) are shown. The filtering happens in the Jinja template, not in Python.

### `POST /habits/<name>/done`

Marks the named habit as done today. Calls `mark_done(db, name)`. Redirects to `/habits`.

### `POST /habits/<name>/undo`

Reverses a same-day completion. Calls `mark_done(db, name, undo=True)`. Redirects to `/habits`.

---

## Budget

### `GET /budget`

Main budget page. Accepts query parameters:

| Parameter | Values | Default | Description |
|---|---|---|---|
| `view` | `month`, `year` | `month` | Monthly or yearly chart |
| `projection` | `on`, (absent) | off | Show projected spend to end of period |
| `provider` | `all`, `monzo`, `nationwide`, `amex` | `all` | Filter to a specific bank |
| `offset` | `0`, `-1` | `0` | `0` = current month, `-1` = previous month |

### `POST /budget/settings`

Saves income settings for a given month. Form fields: `year`, `month`, `base_income`, `extra_income`, `notes`, `view`, `provider`, `offset`.

### `POST /budget/reclassify`

Stores a category override for a transaction description. Form fields: `description`, `category`, `view`, `provider`, `offset`.

The override is stored in the `category_overrides` table, keyed on the description lowercased. Takes effect immediately on the next page load.

### `POST /budget/sinking-fund`

Adds or removes a sinking fund override for a transaction description. Form fields: `description`, `action` (`add` or `remove`), `view`, `provider`, `offset`.

### `POST /budget/savings-baseline`

Saves month-end savings balances. Form fields: `year`, `month`, one field per savings account named `baseline_<account_name_lowercased_underscored>`.

---

## TrueLayer OAuth

### `GET /auth/connect/<provider>`

Initiates OAuth for `monzo`, `nationwide`, or `amex`. Generates a PKCE code verifier and CSRF state token, stores them in `oauth_state` with a 10-minute TTL, and redirects to TrueLayer.

### `GET /auth/callback`

OAuth callback. Exchanges the code for tokens, validates the state token, stores access/refresh tokens in `tl_tokens`. Redirects to `/budget`.

### `POST /auth/disconnect/<provider>`

Deletes stored tokens for the provider. Redirects to `/budget`.

---

## Debug

### `GET /debug`

Renders the page transition tester. Dev only.

### `GET /debug/transactions/<provider>`

Returns a JSON array of all recent transactions from the given provider, with their TrueLayer classification and the category `map_category()` assigns them. Useful for diagnosing categorisation issues.
