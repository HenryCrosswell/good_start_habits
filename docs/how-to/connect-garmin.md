# Connect Garmin

This guide covers the one-time setup needed to pull your running data into the `/garmin` dashboard.

---

## Prerequisites

- You have a Garmin Connect account with running activities recorded from 2026 onwards.
- `ANTHROPIC_API_KEY` is set in your `.env` if you want the AI coaching summary.

---

## Token file

The dashboard uses the same `garmin_tokens.json` file as the Garmin MCP tool. If the MCP is already working, the tokens are already at `~/.garminconnect/garmin_tokens.json` and no further auth setup is needed locally.

If you need to generate tokens from scratch (e.g. fresh machine or Railway):

```bash
uv run python -c "
import garminconnect, getpass
api = garminconnect.Garmin(input('Email: '), getpass.getpass('Password: '))
api.login(tokenstore='~/.garminconnect')
print('Tokens saved to ~/.garminconnect/garmin_tokens.json')
"
```

Garmin may prompt for an MFA code during this step.

---

## Step 2 — Trigger the initial backfill

The background scheduler polls every 30 minutes automatically, but you can force an immediate sync:

```bash
curl -X POST http://localhost:5000/garmin/sync
```

This fetches all running activities since 1 January 2026. For ~20 activities it takes about 15 seconds (0.3 s delay between split fetches to avoid rate-limiting).

---

## Railway deployment

Set these environment variables in the Railway dashboard:

| Variable | Value |
|---|---|
| `GARMIN_TOKENS_DIR` | `/data/.garminconnect` |
| `ANTHROPIC_API_KEY` | your Anthropic API key |

Then authenticate once via the Railway shell:

```bash
python -c "
import garminconnect, getpass, os
token_dir = os.environ.get('GARMIN_TOKENS_DIR', '/data/.garminconnect')
api = garminconnect.Garmin(input('Email: '), getpass.getpass('Password: '))
api.login(tokenstore=token_dir)
print('Tokens saved to', token_dir)
"
```

After that, the scheduler handles everything automatically. Tokens survive deploys because they are written to the persistent `/data` volume.

---

## How the Efficiency Factor is calculated

EF = **run speed (km/h) ÷ avg heart rate (bpm)**

For each activity the app fetches per-lap splits and sums only the `ACTIVE` (running) laps — excluding walk-break laps — to compute a true run pace. This prevents activities with long walk intervals from appearing artificially slow.

Example: 400 m × 8 ACTIVE laps = 3 200 m in 980 s → 5:06/km → 11.76 km/h ÷ 165 bpm = **EF 0.071**

A rising EF line means you are getting faster at the same heart rate, or your heart rate is dropping at the same speed — the key signal of improving aerobic fitness.
