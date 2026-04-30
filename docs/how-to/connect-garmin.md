# Connect Garmin

This guide covers the one-time setup needed to pull your running data into the `/garmin` dashboard.

---

## Prerequisites

- You have a Garmin Connect account with running activities recorded from 2026 onwards.
- `ANTHROPIC_API_KEY` is set in your `.env` if you want the AI coaching summary.

---

## Step 1 — Authenticate locally

Run this once in the project shell to save your Garmin credentials via `garth`:

```bash
uv run python -c "
import garth, getpass
garth.login(input('Email: '), getpass.getpass('Password: '))
garth.dump('~/.garth')
print('Done — tokens saved to ~/.garth/')
"
```

Garmin may prompt for an MFA code. Tokens are saved to `~/.garth/` and refreshed automatically.

---

## Step 2 — Trigger the initial backfill

The background scheduler polls every 30 minutes, but you can force an immediate sync:

```bash
curl -X POST http://localhost:5000/garmin/sync
```

This fetches all running activities since 1 January 2026. For ~20 activities it takes about 15 seconds (0.3 s delay between split fetches to avoid rate-limiting).

---

## Railway deployment

Set these environment variables in the Railway dashboard:

| Variable | Value |
|---|---|
| `GARMIN_TOKENS_DIR` | `/data/.garth` |
| `ANTHROPIC_API_KEY` | your Anthropic API key |

Then authenticate once via the Railway shell:

```bash
python -c "
import garth, getpass, os
garth.login(input('Email: '), getpass.getpass('Password: '))
garth.dump(os.environ.get('GARMIN_TOKENS_DIR', '/data/.garth'))
"
```

After that, the scheduler handles everything automatically.

---

## How the Efficiency Factor is calculated

EF = **run speed (km/h) ÷ avg heart rate (bpm)**

For each activity the app fetches per-lap splits and sums only the `ACTIVE` (running) laps — excluding walk-break laps — to compute a true run pace. This prevents activities with long walk intervals from appearing artificially slow.

Example: 400 m × 8 ACTIVE laps = 3 200 m in 980 s → 5:06/km → 11.76 km/h ÷ 165 bpm = **EF 0.071**

A rising EF line means you are getting faster at the same heart rate, or your heart rate is dropping at the same speed — the key signal of improving aerobic fitness.
