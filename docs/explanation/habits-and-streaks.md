# Explanation: Habits and streaks

---

## Why habits work the way they do

The dashboard is not a nag machine. It doesn't send notifications, escalate urgency, or punish you for missing days. The habit page exists to be glanced at passively — it rotates into view on the clock's schedule, you notice your streaks, you decide what to do. That's it.

This philosophy shapes every streak rule.

---

## How `daily_maintenance()` works

`daily_maintenance()` is called every time the `/habits` page loads. It compares `last_completed` for each habit against today's date and applies one of four cases:

| Days since last completion | What happens |
|---|---|
| 0 (same day) | Nothing — you already handled it today |
| 1 | Resets `done_today` to 0 so the button is available again |
| 2 | Resets `done_today` to 0 and logs a warning — you have today to catch up before the streak breaks |
| 3 or more | Resets `done_today` to 0 and zeros the streak |

The 2-day grace period is intentional. Missing one day doesn't break your streak as long as you complete the habit the next day. Missing two days in a row does.

---

## Why `last_completed` is used instead of `done_today`

`done_today` is reset every day, so it can't tell you how long ago you last completed something. `last_completed` is the durable record. The difference between `last_completed` and today tells `daily_maintenance()` exactly which case applies.

---

## Habit visibility vs habit existence

Every habit in `config.HABITS` always has a row in the `habits` table. Visibility on the page is controlled by `HABIT_ACTIVE_DAYS` — the Jinja template filters the list against today's day name before rendering.

This means a habit not scheduled for today simply doesn't appear. Its streak is not affected. When it appears again on its scheduled day, `daily_maintenance()` runs as normal and applies the rules above.

---

## What the streak actually measures

The streak counts consecutive days on which the habit was marked done, subject to the rules above. It is not a count of completions — it is a count of days without breaking the chain. Missing a scheduled day resets it; completing it on an unscheduled day is not possible (the button isn't there).

---

## Undo

Clicking UNDO on the same day reverses the completion: `done_today` goes back to 0 and the streak decrements by 1. Undo is only effective on the day of completion — there is no way to retroactively change a past day.
