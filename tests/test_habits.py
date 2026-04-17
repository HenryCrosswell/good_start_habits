from good_start_habits.habits import (
    day_diff,
    daily_reset,
    mark_done,
    incomplete_tasks,
)
import pytest
from typing import Any

list_of_dates: list[tuple[str, str, int]] = [
    ("2026-04-01", "2026-04-10", 9),
    ("2026-04-01", "2026-05-01", 30),
    ("2025-12-31", "2026-01-05", 5),
    ("1", "0", 0),
    ("56", "2026-04-10", 0),
]

json_list: list[dict[str, Any]] = [
    {
        "last_written": None,
        "SPF applied": {"streak": 0, "last_completed": None, "done_today": False},
    },
    {
        "last_written": "2026-04-10",
        "Piano practice": {
            "streak": 0,
            "last_completed": "2026-04-10",
            "done_today": True,
        },
    },
    {
        "last_written": "2026-04-10",
        "Run logged": {
            "streak": 12,
            "last_completed": "2026-04-01",
            "done_today": False,
        },
    },
    {
        "last_written": "2026-01-05",
        "None": {"streak": 125, "last_completed": "2026-01-01", "done_today": False},
    },
]


@pytest.fixture
def test_json():
    base_json: dict[str, Any] = {
        "last_written": None,
        "SPF applied": {"streak": 0, "last_completed": None, "done_today": False},
    }
    return base_json


@pytest.mark.parametrize("previous_date, current_date, expected", list_of_dates)
def test_day_diff(previous_date: str, current_date: str, expected: int):
    assert day_diff(previous_date, current_date) == expected


@pytest.mark.parametrize("json_dict", json_list)
def test_daily_reset(mocker: Any, json_dict: dict[str, Any]):
    last_written_date, habit_dict = [y for x, y in json_dict.items()]
    keys, values = [a for z, a in habit_dict]
    mocker.patch("good_start_habits.habits.save_state")
    daily_reset(json_dict)
    ...


def test_mark_done():
    mark_done()
    ...


def test_incomplete_tasks():
    incomplete_tasks()
    ...
