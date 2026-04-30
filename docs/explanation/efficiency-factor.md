# Efficiency Factor — what it measures and why it matters

## What is Efficiency Factor?

Efficiency Factor (EF) is a single number that describes how efficiently your cardiovascular system delivers speed. It is calculated as:

```
EF = run speed (km/h) ÷ average heart rate (bpm)
```

A run at 5:06/km (≈ 11.76 km/h) with an average HR of 165 bpm gives:

```
EF = 11.76 / 165 = 0.071
```

## Why use run pace, not total pace?

Activities with walk-break intervals report two different paces:

- **Total pace** (e.g. 6:34/km) — total distance including walks divided by total elapsed time
- **Run pace** (e.g. 5:06/km) — derived from the ACTIVE laps only, ignoring rest/walk laps

Using total pace artificially lowers EF on days with more walk breaks, punishing the format rather than measuring fitness. The dashboard fetches per-lap splits from Garmin, sums only `ACTIVE` laps, and computes run speed from those — so the EF chart reflects running effort consistently regardless of how much you walked.

## How to read the chart

| What the EF line does | What it means |
|---|---|
| **Rising** | You are getting faster at the same HR, or your HR is falling at the same speed. Aerobic fitness is improving. |
| **Flat** | Fitness is being maintained. You are not yet adapting further. |
| **Falling** | Your heart is working harder to hold the same speed. Could be fatigue, illness, or accumulated training stress. |

Short-term dips after hard sessions are normal. Look at the 5-run rolling average (purple dashed line) to see the underlying trend rather than reacting to individual sessions.

## Limitations

EF is most useful for comparing **similar run types** at **low to moderate intensity**. It is less reliable when:

- Max HR varies significantly session to session (e.g. a race vs an easy jog)
- External conditions differ substantially (heat increases HR at a given pace)
- The run is very short (HR may not have fully risen into steady state)

Track the trend over weeks and months, not individual sessions.

## How the summary is generated

After each new activity, the dashboard sends a compact JSON payload (last 10 runs, trend %) to a small language model acting as a running coach. The model is prompted to highlight specific numbers and suggest one actionable tip. The response is cached in SQLite and only regenerated when a new activity appears, minimising API cost.
