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
from typing import Any
from good_start_habits.config import HABITS
from loguru import logger


def load_state():
    with open(pathlib.Path(__file__).parent / "state.json") as json_data:
        state_json = json.load(json_data)
        return state_json


def save_state(state_json: dict[str, Any]):
    with open(pathlib.Path(__file__).parent / "state.json", "w") as json_data:
        json.dump(state_json, json_data, indent=4)


def state_init(state_json: dict[str, Any]):
    """
    Initiliasis the Json if not already populated

    Args:
        state_json (dict[str, Any])
    """
    for habits in HABITS:
        if habits not in state_json:
            state_json[habits] = {
                "streak": 0,
                "last_completed": None,
                "done_today": False,
            }
            logger.info(f"{habits} added to json")

    save_state(state_json)


def day_diff(previous_date: str, current_date: str):
    try:
        date1 = datetime.strptime(previous_date, "%Y-%m-%d")
        date2 = datetime.strptime(current_date, "%Y-%m-%d")
    except Exception as e:
        print(e)
        return 0
    return (date2 - date1).days


def daily_maintenance(state_json: dict[str, Any]):
    """
    check states of whether a habit was done today and
    whether the streak should be reset

        Args:
        state_json (dict[str, Any]): dict {
        "streak": int,
        "last_completed": str,
        "done_today": bool
        }
    """
    cur_date = str(date.today())

    for habit_name, habit_dict in state_json.items():
        stored_date = habit_dict["last_completed"]
        if not stored_date:  # checks if value not null
            stored_date = cur_date
        days_between = day_diff(stored_date, cur_date)
        match days_between:
            case 0:
                continue
            case 1:
                habit_dict["done_today"] = False

            case 2:
                habit_dict["done_today"] = False
                print(f"Only one more day to complete {habit_name} before it resets.")

            case _:
                habit_dict["streak"] = 0
                habit_dict["done_today"] = False
                print(f"Too late! {habit_name}'s streak has been reset")

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
