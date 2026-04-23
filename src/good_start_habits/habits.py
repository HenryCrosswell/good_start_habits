"""
habits.py
- populate state.json with habits, whether it was completed?, and streak count
- day tracker - if more than two days have passed it will reset streak
- day tracker - daily reset app checklists to reset
- day tracker - if checkbox clicked more than once doesn't affect the streak
"""

from datetime import datetime, date
from good_start_habits.config import ACTIVE_TIMES
import sqlite3


def day_diff(previous_date: str, current_date: str):
    try:
        date1 = datetime.strptime(previous_date, "%Y-%m-%d")
        date2 = datetime.strptime(current_date, "%Y-%m-%d")
    except Exception as e:
        print(e)
        return 0
    return (date2 - date1).days


def daily_maintenance():
    con = sqlite3.connect("dashboard.db")
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


def mark_done(habit_name: str):
    """To occur as a result of the checkbox, checks current state_json file
    to see if it has been checked today and increments the string.

    Args:
        state_json (_type_): _description_
        habit_name (str): _description_
    """
    con = sqlite3.connect("dashboard.db")
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
    current_date = datetime.now().strftime("%A")
    current_time = datetime.now().strftime("%H:%M:%S")
    start_time, end_time = ACTIVE_TIMES[current_date]
    if start_time <= current_time <= end_time:
        return True
    else:
        return False
