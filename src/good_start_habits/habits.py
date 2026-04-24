"""Streak logic and daily maintenance for habit tracking."""

from datetime import datetime, date
from good_start_habits.config import ACTIVE_TIMES
import sqlite3


def day_diff(previous_date: str, current_date: str):
    """Days elapsed between two dates.

    Args:
        previous_date: Earlier date as YYYY-MM-DD string.
        current_date: Later date as YYYY-MM-DD string.

    Returns:
        Number of days between the two dates, or 0 on parse error.
    """
    try:
        date1 = datetime.strptime(previous_date, "%Y-%m-%d")
        date2 = datetime.strptime(current_date, "%Y-%m-%d")
    except Exception as e:
        print(e)
        return 0
    return (date2 - date1).days


def daily_maintenance(con: sqlite3.Connection):
    """Resets done_today each new day and zeroes streaks missed by 2+ days.

    Args:
        con: Active SQLite connection, typically from get_db().
    """
    cur = con.cursor()
    cur.execute("""
        SELECT name, streak, last_completed, done_today FROM habits
                """)

    current_date = str(date.today())
    for name, _, last_completed, _ in cur.fetchall():
        if not last_completed:  # checks if value not null
            cur.execute(
                """
            UPDATE habits SET last_completed = ? WHERE name = ?
            """,
                (current_date, name),
            )
            last_completed = current_date

        days_between = day_diff(last_completed, current_date)
        match days_between:
            case 0:
                continue
            case 1:
                cur.execute(
                    """
                UPDATE habits SET done_today = 0 WHERE name = ?
                """,
                    (name,),
                )

            case 2:
                cur.execute(
                    """
                UPDATE habits SET done_today = 0 WHERE name = ?
                """,
                    (name,),
                )
                print(f"Only one more day to complete {name} before it resets.")

            case _:
                cur.execute(
                    """
                UPDATE habits SET done_today = 0, streak = 0 WHERE name = ?
                """,
                    (name,),
                )
                print(f"Too late! {name}'s streak has been reset")
    con.commit()


def mark_done(con: sqlite3.Connection, habit_name: str):
    """Marks a habit complete for today and increments its streak.

    No-op if the habit is already marked done today.

    Args:
        con: Active SQLite connection, typically from get_db().
        habit_name: Name of the habit to mark as done.
    """
    cur = con.cursor()
    today = str(date.today())
    cur.execute(
        """
        SELECT name, done_today FROM habits WHERE name = ?
                """,
        (habit_name,),
    )
    (name, done_today) = cur.fetchone()
    if not done_today:
        cur.execute(
            """
        UPDATE habits SET done_today = 1, streak = streak + 1, last_completed = ? WHERE name = ?
        """,
            (today, name),
        )
    con.commit()


def check_current_datetime() -> bool:
    """Checks whether the current time is within today's active hours.

    Returns:
        True if within active hours, False otherwise.
    """
    current_date = datetime.now().strftime("%A")
    current_time = datetime.now().strftime("%H:%M:%S")
    start_time, end_time = ACTIVE_TIMES[current_date]
    if start_time <= current_time <= end_time:
        return True
    else:
        return False
