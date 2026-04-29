# Explanation: Rotation and active hours

---

## The design intent

The dashboard is meant to be a passive presence, not an active one. The clock is the default view — quiet, undemanding. The screen change from clock to habits is what draws the eye. You glance at your streaks, you decide whether to act, the clock comes back.

This is deliberately different from a notification. A notification demands attention. A screen transition just appears and waits.

---

## Active hours

`config.ACTIVE_TIMES` defines a time window per day. Outside that window:
- The clock shows a quiet message instead of the rotation timer
- The JavaScript navigation system does not navigate away from the clock
- The habits page is still accessible by navigating to `/habits` directly

Within active hours, the clock page sets a JavaScript timer (`ROTATION_INTERVAL` seconds) and navigates to `/habits` when it fires.

The habits page sets a different timer (`DWELL_TIME` seconds) and navigates back to `/` when it fires.

Both timers reset if you interact with the page (clicking a habit button). This gives you time to complete habits without the page switching away mid-action.

---

## Why the interval is randomised

`ROTATION_INTERVAL` and `DWELL_TIME` are currently randomised on each app start:

```python
ROTATION_INTERVAL = randint(1800, 7200)
DWELL_TIME = randint(300, 600)
```

A fixed interval becomes predictable and easy to tune out. A random interval means the screen changes at unpredictable times — you can't subconsciously learn to ignore it. The randomisation is per-app-start, not per-rotation, so within a session the interval is fixed.

Replace `randint(...)` with a fixed value in `config.py` once you have settled on a rhythm that works.

---

## How the JavaScript navigation works

`static/transitions.js` controls navigation. On each rotation it picks a random CSS transition from `transitions.css` (fade, scale, rotate, star wipe, sparkle, etc.), applies it, and then navigates. The varied visual effect reinforces the passive attention-catching goal — a different transition each time is harder to tune out than a uniform one.

The sparkle transition is intentionally less common than others (lower weight in the random selection).

---

## The `?freeze=1` parameter

Adding `?freeze=1` to the URL disables the automatic rotation timer on the clock page. Useful when you want to check something on the budget page without the clock constantly navigating away.
