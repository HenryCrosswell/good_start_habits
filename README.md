# good-start-habits

A personal dashboard that lives in a browser tab (or a Raspberry Pi screen). It shows your habits, budget, and a standby clock. During active hours the screen cycles between the clock and your habit checklist — no notifications, no nagging, just a passive glance when the display changes.

Built with Flask, SQLite, and Plotly. No external CSS frameworks, no JavaScript build step.

---

## Quick start

```bash
# Install dependencies
uv sync

# Create your .env file (see Configuration below)
cp .env.example .env  # or create it manually

# Run
flask --app src/good_start_habits/app.py run
```

The app will be at `http://localhost:5000`. The database (`dashboard.db`) is created automatically on first run.

---

## Project structure

```
src/good_start_habits/
├── app.py          # Flask app and all route handlers
├── config.py       # Everything you'll want to change — habits, hours, budgets
├── habits.py       # Streak logic: daily maintenance, mark done, active hours check
├── db.py           # SQLite connection management and schema creation
├── budget.py       # Transaction categorisation and Plotly chart generation
├── truelayer.py    # TrueLayer OAuth client and banking data API wrapper
├── templates/
│   ├── base.html   # Shared HTML skeleton, fonts, CSS variables
│   ├── clock.html  # Standby page with animated clock
│   ├── habits.html # Daily habit checklist with streaks
│   ├── budget.html # Budget dashboard with charts
│   └── debug.html  # Page transition tester (dev only)
└── static/
    ├── style.css
    ├── transitions.css  # Keyframe animations for page transitions
    └── transitions.js   # Navigation system with randomised transition effects
tests/
├── test_db.py
├── test_habits.py
├── test_budget.py
└── test_truelayer.py
```

---

## Configuration

Almost everything you'd want to change lives in `config.py` and `.env`.

### `.env` — secrets and environment flags

```
SECRET_KEY=<any long random string>        # Flask session signing key
TRUELAYER_CLIENT_ID=<from TrueLayer app>
TRUELAYER_CLIENT_SECRET=<from TrueLayer app>
TRUELAYER_REDIRECT_URI=http://localhost:5000/auth/callback
TRUELAYER_SANDBOX=true                     # Set to false to use real bank connections
```

`SECRET_KEY` is required even if you're not using the budget features. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.

`TRUELAYER_SANDBOX=true` keeps you in TrueLayer's test environment with fake data. Flip to `false` and update the credentials only when you're ready for real bank connections.

---

### `config.py` — the main control panel

#### Habits

**`HABITS`** — the list of habit names tracked by the app. Add, remove, or rename entries here. Each name must also appear in `HABIT_ACTIVE_DAYS`.

**`HABIT_ACTIVE_DAYS`** — controls which days each habit appears. A habit won't show up on days it's not listed, so you can schedule habits to specific days of the week.

```python
# Example: make "Piano practice" weekdays only
"Piano practice": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
```

#### Active hours

**`ACTIVE_TIMES`** — the window each day when the dashboard is "live". Outside this window the clock shows a quiet message and the habit page rotation stops. Times are 24-hour `HH:MM:SS` strings.

```python
ACTIVE_TIMES = {
    "Monday": ("06:00:00", "21:00:00"),
    ...
    "Saturday": ("08:00:00", "21:00:00"),
}
```

#### Clock rotation

**`ROTATION_INTERVAL`** — seconds before the clock auto-navigates to the habits page (when active). Currently randomised between 5 and 15 on each app start. Replace `randint(5, 15)` with a fixed value like `1800` (30 min) once you've decided on an interval.

**`DWELL_TIME`** — seconds the habits page stays visible before returning to the clock. Same deal — randomised now, fix it when you're happy.

#### Budget limits

**`BUDGET_LIMITS`** — your monthly spending limits per category, in pounds. This is what the budget page compares actual spend against.

```python
BUDGET_LIMITS = {
    "Groceries": 200.0,
    "Food & Coffee": 80.0,
    "Eating Out & Social": 120.0,
    "Transport": 480.0,
    ...
}
```

**`PROVIDER_BUDGET_LIMITS`** — per-bank category caps. Useful when a category is split across accounts (e.g. train tickets on Amex, parking on Nationwide). When you filter the budget page to a specific bank, these limits apply instead of the global ones.

#### Transaction categorisation

**`CATEGORY_MAP`** — maps TrueLayer's transaction classifications (their taxonomy) to your personal categories. Keys with a `|` match both the top-level and sub-level classification; plain keys match top-level only. A value of `None` excludes the transaction from all spending totals (used for transfers and income).

**`DESCRIPTION_PATTERNS`** — fallback list for transactions TrueLayer can't classify, or where the classification isn't specific enough. Matched case-insensitively as substrings, first match wins. Add new entries here when you spot a recurring merchant landing in the wrong category.

```python
DESCRIPTION_PATTERNS = [
    ("tesco", "Food & Coffee"),
    ("zizzi", "Eating Out & Social"),
    ("trainline", "Transport"),
    ("transfer to", None),  # None = exclude entirely
    ...
]
```

---

## Pages and routes

| Route | Method | What it does |
|---|---|---|
| `/` | GET | Standby clock. Rotates to `/habits` during active hours. |
| `/habits` | GET | Today's habit checklist. Calls `daily_maintenance()` on load. |
| `/habits/<name>/done` | POST | Marks a habit done, increments streak. Redirects back. |
| `/habits/<name>/undo` | POST | Undoes a same-day completion. Redirects back. |
| `/budget` | GET | Budget dashboard. Accepts `?view=month\|year`, `?projection=1`, `?provider=monzo\|...` |
| `/auth/connect/<provider>` | GET | Starts TrueLayer OAuth for `monzo`, `nationwide`, or `amex`. |
| `/auth/callback` | GET | OAuth callback — exchanges code for tokens, saves to SQLite. |
| `/auth/disconnect/<provider>` | POST | Removes stored tokens for a provider. |
| `/debug` | GET | Page transition tester. |

---

## How habits work

When you visit `/habits`, `daily_maintenance()` runs first. It checks when each habit was last completed and applies these rules:

- **Same day** — no change.
- **1 day ago** — resets `done_today` so the button is available again.
- **2 days ago** — resets `done_today`, logs a warning. Streak is preserved (one missed day doesn't break it).
- **3+ days ago** — resets both `done_today` and `streak` to zero.

Clicking "DONE" increments the streak and records today's date. Clicking "UNDO" on the same day reverses it. Streaks are stored in SQLite so they survive restarts.

---

## How the budget works

The budget page fetches the last 30 days of transactions from any connected bank accounts (TrueLayer Data API), then categorises each transaction using the logic in `budget.py`:

1. Check `CATEGORY_MAP` for a match on TrueLayer's `transaction_classification` field.
2. If no match, scan `DESCRIPTION_PATTERNS` for a substring match on the transaction description.
3. Fall back to `"Other"`.
4. If the result is `None` (transfer, income, internal payment) — exclude from totals.

Charts are built with Plotly and rendered in the browser. The primary view is a burn-rate line graph — one line per category, x-axis is days of the month, y-axis is cumulative spend. A dotted horizontal line marks the budget limit. Toggle projection on to see a linear extrapolation to month-end.

OAuth tokens are stored in SQLite (not `.env`) because they refresh frequently. An APScheduler background job refreshes tokens hourly. Tokens are also checked and refreshed on-demand before each API call.

---

## Database

SQLite, stored in `dashboard.db` in the working directory. Created automatically — you never need to run migrations manually.

| Table | Purpose |
|---|---|
| `habits` | One row per habit: name, streak, last_completed date, done_today flag |
| `tl_tokens` | OAuth access/refresh tokens per provider, with expiry timestamp |
| `oauth_state` | Single-use PKCE + CSRF state tokens during OAuth flow (10-minute TTL) |

---

## Running tests

```bash
pytest
```

Tests use in-memory SQLite — they don't touch `dashboard.db` or make network calls. The test suite covers streak logic, database initialisation, transaction categorisation, and TrueLayer OAuth helpers.

```bash
pytest -v              # verbose output
pytest tests/test_budget.py   # single file
pytest --cov=src       # with coverage
```

---

## Linting and formatting

```bash
ruff check .           # lint
ruff format .          # format
mypy src/              # type check
```

---

## Adding a new habit

1. Add the name to `HABITS` in `config.py`.
2. Add it to `HABIT_ACTIVE_DAYS` with the days you want it to appear.
3. Restart the app — `db.py` uses `INSERT OR IGNORE`, so the new row is added automatically without touching existing data.

## Adding a new spending category

1. Add it to `BUDGET_LIMITS` in `config.py` with a monthly limit.
2. Add classification mappings to `CATEGORY_MAP` (if TrueLayer's taxonomy covers it).
3. Add description patterns to `DESCRIPTION_PATTERNS` for merchants that won't match by classification.
4. Optionally add per-provider limits to `PROVIDER_BUDGET_LIMITS`.

---

## What's built and what's next

| Phase | Status | What |
|---|---|---|
| Flask scaffold + SQLite | Done | Routes, DB, habit storage |
| Standby clock + active hours | Done | Clock page, passive rotation |
| Habits page | Done | Checklist, streaks, undo |
| Budget page (TrueLayer) | Mostly done | OAuth, charts, categorisation — UI refinement ongoing |
| Strava integration | Planned | Auto-tick "Track run" when a run is logged |
| Hevy integration | Planned | Auto-tick "Track workout" when a session is logged |
| Raspberry Pi deployment | Planned | systemd service, Chromium kiosk mode |

---

## Conventions

- Credentials go in `.env` — never hardcoded, never committed.
- `dashboard.db` and `.env` are gitignored.
- Each integration returns a bool or a list — no UI logic inside integrations.
- If an integration fails, log it and fall back to the manual button — never crash the app.
- Business logic lives in Python — Jinja templates stay thin.
- No external CSS frameworks — plain CSS only.


---

## Budget review & financial planning notes

> Last reviewed: 2026-04-27. Based on **real transaction data** from Monzo, Nationwide, and Amex
> via TrueLayer — 4 months of history (2026-01 through 2026-04). Averages below are monthly means
> across all captured months. Some months have incomplete data (see caveats).

### Measured spending averages (Jan–Apr 2026, 4 months)

| Category | Budget | Measured avg/mo | vs budget | Notes |
|---|---|---|---|---|
| Rent | £1,460 | £738 | −£722 | Only 2 standing orders captured (March only in window) — not meaningful yet |
| Bills & Utilities | £242 | £142 | −£100 | Jan had no data; Feb–Apr average is ~£189 — likely correct once full months land |
| Transport | £480 | £176 | −£304 | Historic Amex train data was lost before the card sign-convention fix (2026-04-27) — recheck next month |
| Groceries | £200 | £119 | −£81 | Jan had no Amex data; Apr alone was £221 (over budget) — monitor |
| Food & Coffee | £80 | £98 | **+£18** | Consistently over; Tesco small shops and coffees adding up |
| Eating Out & Social | £120 | £118 | −£2 | Essentially on budget, but see "Other" caveats below |
| Subscriptions | £89 | £26 | −£63 | Anthropic/Claude (~£18) on Amex is missing provider limit — triggers WRONG CARD |
| Personal Care | £51 | £39 | −£12 | Reasonable; no provider assigned so appears as WRONG CARD |
| Entertainment | £15 | £11 | −£4 | Underbudgeted — March alone was £34 |
| Other | £52 | **£345** | **+£293** | Severely inflated — see miscategorisation notes below |

**Data caveats:**
- Rent: TrueLayer only returned the March 30 standing order — Jan/Feb payments pre-date the connection window. Will normalise once a full quarter is connected.
- Transport: Amex transactions had reversed sign convention until 2026-04-27 fix. Historic Amex train spending was silently dropped. Recheck after a full month post-fix.
- Amex: no data at all in January (connection not yet established).

**"Other" is inflated by miscategorised spending (~£200+/month):**
The following Amex merchants are landing in "Other" and should be "Eating Out & Social". Add them to `DESCRIPTION_PATTERNS` above "paypal":
- `LS NOBLE ROT MAYFAIR` → Eating Out & Social (£210 dinner)
- `PRIME STEAK & GRILL` → Eating Out & Social (£102)
- `BAR TERMINI` → Eating Out & Social (£43)
- `AMZNMKTPLACE` / `AMZNMktplace` → already covered by "amazon" but Amex format differs — check

**PayPal → amrit.kaur fix needed:**
`("paypal", "Other")` sits before `("amrit.kaur", "Bills & Utilities")` in `DESCRIPTION_PATTERNS`, so PayPal payments to her go to Other. Move the `amrit.kaur` pattern above the generic `paypal` line.

---

### The extra_income problem

The default `extra_income = £100` in `config.py` is wrong. Total configured outgoings are
**£2,789/month**. Against a base salary of £2,440 that's already £349 in the red before GF
contribution. The realistic GF contribution is ~£851/month (roughly half of rent £1,460 + bills
£242). Until that number is set correctly the "Income Left" figure on the budget page is
meaningless.

**Recommended default**: set `DEFAULT_EXTRA_INCOME = 851.0` in `config.py`. This gives a
realistic surplus of ~£502/month before savings, which is the number that should drive savings
decisions. Update this each month via the settings panel if it varies.

### Realistic monthly budget (£/month)

| Category | Current limit | Assessment |
|---|---|---|
| Rent | £1,460 | Fixed — correct |
| Bills & Utilities | £242 | Fixed — correct |
| Transport | £480 | £350 Amex (trains/petrol) + £100 Nationwide (parking) = £450 configured in providers. The £30 gap is uncovered — TFL/Uber on Monzo. Add £30 to Monzo provider limits, or raise Amex to £380. |
| Subscriptions | £89 | Nationwide carries £80. Claude/Anthropic (~£18) is on Amex but Amex has no Subscriptions limit → triggers WRONG CARD every month. Add `"Subscriptions": 20.0` to `amex` in `PROVIDER_BUDGET_LIMITS` and reduce `nationwide` to £69 (gym + phone + lastpass + proton). |
| Groceries | £200 | Amex carries £200 — appears correct. |
| Food & Coffee | £80 | Monzo carries £80 — reasonable for misc coffees/snacks. |
| Eating Out & Social | £120 | Monzo carries £120 — possibly low if you're going out regularly; consider £150. |
| Personal Care | £51 | No provider assigned — will appear as WRONG CARD on whichever card you use. Assign to Amex or Monzo in `PROVIDER_BUDGET_LIMITS`. |
| Entertainment | £15 | No provider assigned — same issue. Likely underbudgeted (gigs, Steam, etc.). Consider £30. |
| Other | £52 | No provider assigned. Gifts and clothing are lumpy — this will exceed in some months, be zero in others. |
| **Total outgoings** | **£2,789** | With £851 GF contribution: effective personal outgoings = **£1,938** |

### BUDGET_LIMITS vs PROVIDER_BUDGET_LIMITS — the duplication problem

These two dicts are supposed to represent the same thing at different granularities but are
maintained independently and have already drifted (Transport, Subscriptions). The correct model:

- `PROVIDER_BUDGET_LIMITS` is the **source of truth** for any category tied to a specific card.
- `BUDGET_LIMITS` (used in the "all" view) should be derived by summing provider limits across
  all providers, then adding limits for unassigned categories (Personal Care, Entertainment, Other).

Until the code does this automatically, keep both dicts in sync manually. Every time you change
a provider limit, check whether the corresponding `BUDGET_LIMITS` entry needs updating. Add a
comment to each `BUDGET_LIMITS` entry showing how the number was calculated.

Categories not assigned to any provider (Personal Care, Entertainment, Other) will show as
WRONG CARD on every provider view. Assign them to the card you actually use for those purchases
to suppress the warnings.

### LISA — priority contribution

LISA balance: **£24,434.88**. Government bonus: 25% on up to £4,000/year = **£1,000 free per
year**. To max this, contribute **£333/month**. This is effectively a guaranteed 25% return —
nothing else competes with it. Treat it as a fixed expense, not discretionary savings. Track it
via the Atom sinking fund pattern or as a direct outgoing in extra_income if Moneybox auto-debits.

### AJ Bell ISA

Balance: **£7,119.36** in an adventurous (higher-risk) account. At 7% blended return: ~£498/year
passive growth. Annual ISA allowance is £20,000; once the LISA is maxed, surplus savings should
flow here. No action needed unless you want to increase monthly contributions.

### Premium Bonds

Balance: **£1,025** at 4.4% average prize rate (~£45/year, tax-free). Prize equivalent is decent
but below AJ Bell expected return. Keep at current level; don't grow this over ISA contributions.

### Atom — sinking fund, not long-term savings

Atom is a sinking fund for emergency, holiday, car, and other lumpy planned costs. 5% fixed rate.
**Do not count it as investment savings.** The key accounting rule:

> When a large purchase is **covered by a prior Atom transfer** (holiday hotel, car service, etc.),
> use the **reclassify feature** on that transaction to mark it as `Transfer` (excluded from spend
> totals). You already saved for it; counting it as spending double-charges your budget.

Categories you're pre-funding via Atom (holiday, car repair) should not have budget limits in
`BUDGET_LIMITS` unless you want to track them separately. If they appear in transactions and you
haven't reclassified them, they'll land in `Other` and make your discretionary spend look high.

### Nationwide savings (£1,000 at 6.5%)

Easy-access at 6.5% is excellent. This appears in transactions as transfers (already excluded).
The savings baseline feature tracks the balance — keep that updated monthly.

---

## TO-DO (engineering backlog)

- add Noble Rot, Prime Steak & Grill, Bar Termini to DESCRIPTION_PATTERNS as Eating Out & Social (currently landing in Other)
- move amrit.kaur pattern above paypal in DESCRIPTION_PATTERNS (paypal matches first → Other instead of Bills & Utilities)
- add budget to rotation alongside habits and clock
- graph y-axis should always show 0 (rangemode: tozero)
- add check: if Amrit Paypal is £80–£115 → Bills & Utilities, else → Other
- graph swap timer: 2 minutes after interaction, 25 seconds idle
- interactive transactions: inline edit button with "just this time" vs "always" reclassify
- track one month in the past — active month selector in the header
- remove daily spend chart — not useful when categories are tracked
- personalised income panel: preload previous month's settings as defaults each new month
- add vector images to habit card edges (90s/gaming theme)
- make sparkle transition more common in rotation
- PROVIDER_BUDGET_LIMITS: add Subscriptions to Amex (Claude/Anthropic), assign Personal Care and Entertainment to a provider to stop WRONG CARD false positives
- Fix Transport gap: £480 total but only £450 across provider limits — add ~£30 Monzo transport for TFL/Uber
