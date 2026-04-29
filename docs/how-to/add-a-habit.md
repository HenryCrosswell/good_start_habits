# How to add, remove, or rename a habit

All habit configuration lives in `config.py`. You do not need to touch the database manually.

---

## Add a habit

1. Add the habit name to the `HABITS` list in `config.py`.
2. Add it to `HABIT_ACTIVE_DAYS` with the days you want it to appear.

```python
# HABITS
HABITS = [
    ...
    "Cold shower",   # add here
]

# HABIT_ACTIVE_DAYS
HABIT_ACTIVE_DAYS = {
    ...
    "Cold shower": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}
```

3. Restart the app.

On restart, `db.py` uses `INSERT OR IGNORE` to add the new row to the `habits` table. Existing habit rows and their streaks are untouched.

---

## Remove a habit

1. Remove it from `HABITS`.
2. Remove it from `HABIT_ACTIVE_DAYS`.
3. Restart the app.

The row remains in the database but will never appear in the UI. If you want to clean it up from the database, run:

```bash
sqlite3 dashboard.db "DELETE FROM habits WHERE name = 'Habit name';"
```

---

## Rename a habit

Renaming is a remove + add. The old row stays in the database and the new name gets a fresh row with a zero streak.

1. Remove the old name from `HABITS` and `HABIT_ACTIVE_DAYS`.
2. Add the new name to both.
3. Restart the app.

If you want to carry the streak across, update the database directly:

```bash
sqlite3 dashboard.db "UPDATE habits SET name = 'New name' WHERE name = 'Old name';"
```

---

## Change which days a habit appears

Edit the day list in `HABIT_ACTIVE_DAYS`. Days are full English names with a capital letter: `"Monday"`, `"Tuesday"`, etc.

No restart required for this — the template reads `HABIT_ACTIVE_DAYS` on every page load.

Wait — actually a restart is required because `config.py` is loaded at import time. Restart the app after changing `HABIT_ACTIVE_DAYS`.
