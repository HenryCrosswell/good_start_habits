# Reference: Database

SQLite, stored in `dashboard.db` in the working directory (`/app/dashboard.db` in Docker). Created automatically on first run — you never need to run migrations manually. All tables use `CREATE TABLE IF NOT EXISTS`.

---

## Tables

### `habits`

One row per habit.

| Column | Type | Description |
|---|---|---|
| `name` | `TEXT PRIMARY KEY` | Habit name (matches `config.HABITS`) |
| `streak` | `INTEGER NOT NULL DEFAULT 0` | Current consecutive-day streak |
| `last_completed` | `TEXT` | Date of last completion as `YYYY-MM-DD`, or NULL |
| `done_today` | `INTEGER NOT NULL DEFAULT 0` | 1 if completed today, 0 otherwise |

New habits are inserted via `INSERT OR IGNORE` on startup — existing rows are untouched.

---

### `tl_tokens`

OAuth tokens for each TrueLayer provider.

| Column | Type | Description |
|---|---|---|
| `provider` | `TEXT PRIMARY KEY` | `monzo`, `nationwide`, or `amex` |
| `access_token` | `TEXT NOT NULL` | Short-lived access token |
| `refresh_token` | `TEXT` | Long-lived refresh token |
| `expires_at` | `TEXT NOT NULL` | ISO-8601 UTC timestamp |
| `created_at` | `TEXT NOT NULL DEFAULT (datetime('now'))` | Row creation time |

---

### `oauth_state`

Single-use PKCE + CSRF state tokens during the OAuth flow. Each row expires 10 minutes after creation.

| Column | Type | Description |
|---|---|---|
| `state` | `TEXT PRIMARY KEY` | Random CSRF state token |
| `provider_hint` | `TEXT NOT NULL` | Which provider initiated the flow |
| `code_verifier` | `TEXT NOT NULL` | PKCE code verifier |
| `expires_at` | `TEXT NOT NULL` | ISO-8601 UTC timestamp |

---

### `budget_settings`

Income settings per calendar month.

| Column | Type | Description |
|---|---|---|
| `year` | `INTEGER NOT NULL` | |
| `month` | `INTEGER NOT NULL` | |
| `base_income` | `REAL NOT NULL DEFAULT 2440.0` | Monthly salary |
| `extra_income` | `REAL NOT NULL DEFAULT 100.0` | Partner contribution or other |
| `notes` | `TEXT` | Free text notes for the month |

Primary key: `(year, month)`.

---

### `category_overrides`

Per-description category overrides set via the inline reclassify UI.

| Column | Type | Description |
|---|---|---|
| `description_lower` | `TEXT PRIMARY KEY` | Transaction description, lowercased |
| `category` | `TEXT NOT NULL` | Overridden category (or `"Transfer"` to exclude) |
| `created_at` | `TEXT DEFAULT (datetime('now'))` | |

These take priority over `DESCRIPTION_PATTERNS` in `config.py`.

---

### `savings_baseline`

Month-end balances for savings accounts, used to calculate net savings movement.

| Column | Type | Description |
|---|---|---|
| `account` | `TEXT NOT NULL` | Account name (matches `config.SAVINGS_ACCOUNTS[n]["name"]`) |
| `year` | `INTEGER NOT NULL` | |
| `month` | `INTEGER NOT NULL` | |
| `balance` | `REAL NOT NULL DEFAULT 0.0` | Balance at end of month |

Primary key: `(account, year, month)`. The most recent baseline at or before the displayed month is used.

---

### `sinking_fund_overrides`

Transaction descriptions marked as sinking fund (excluded from regular spending).

| Column | Type | Description |
|---|---|---|
| `description_lower` | `TEXT PRIMARY KEY` | Transaction description, lowercased |
| `created_at` | `TEXT DEFAULT (datetime('now'))` | |

---

## Accessing the database directly

```bash
sqlite3 dashboard.db
```

Useful queries:

```sql
-- See all habits and their streaks
SELECT name, streak, done_today, last_completed FROM habits;

-- See stored OAuth tokens
SELECT provider, expires_at FROM tl_tokens;

-- See all category overrides
SELECT * FROM category_overrides;
```
