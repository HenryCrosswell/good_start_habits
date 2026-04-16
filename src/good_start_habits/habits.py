"""
habits.py
- populate state.json with habits, whether it was completed?, and streak count
- day tracker - if more than two days have passed it will reset streak
- day tracker - daily reset app checklists to reset
- day tracker - if checkbox clicked more than once doesn't affect the streak
"""

import pathlib
import json
from datetime import datetime, date
from .config import HABITS
from typing import Any


def load_state():
    with open(pathlib.Path(__file__).parent / "state.json") as json_data:
        state_json = json.load(json_data)
        return state_json


def save_state(state_json: dict[str, Any]):
    with open(pathlib.Path(__file__).parent / "state.json", "w") as json_data:
        json.dump(state_json, json_data, indent=4)


def day_diff(previous_date: str, current_date: str):
    try:
        date1 = datetime.strptime(previous_date, "%Y-%m-%d")
        date2 = datetime.strptime(current_date, "%Y-%m-%d")
    except Exception as e:
        print(e)
        return 0
    return (date2 - date1).days


def daily_reset(state_json: dict[str, Any]):
    """check json file for previous or existing date, if none"""
    cur_date = str(date.today())
    stored_date = state_json["last_written"]

    if not stored_date:  # checks if value is populated
        stored_date = cur_date

    days_between = day_diff(stored_date, cur_date)
    if days_between >= 1:
        state_json["last_written"] = cur_date
        for habit in HABITS:
            state_json[habit]["done_today"] = False

    save_state(state_json)


def mark_done(state_json: dict[str, Any], habit_name: str):
    """To occur as a result of the checkbox, checks current state_json file
    to see if it has been checked today and increments the string.

    Args:
        state_json (_type_): _description_
        habit_name (str): _description_
    """

    habit = state_json[habit_name]
    if not habit["done_today"]:
        habit["done_today"] = True
        habit["streak"] += 1
        habit["last_completed"] = str(date.today())
        save_state(state_json)
    else:
        print(f"The {habit_name} box has already been checked today")


def incomplete_tasks(state_json: dict[str, Any]):
    cur_date = str(date.today())

    for habit in HABITS:
        stored_date = state_json[habit]["last_completed"]
        days_between = day_diff(stored_date, cur_date)
        if days_between > 1:
            state_json[habit]["streak"] = 0
            print(f"Too late! {habit}'s streak has been reset")
        else:
            print(f"Only one more day to complete {habit} before it resets.")
    save_state(state_json)
