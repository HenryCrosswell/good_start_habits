from good_start_habits.habits import (
    day_diff,
    daily_maintenance,
    mark_done,
    state_init,
    check_current_datetime,
)
import pytest
from typing import Any
from datetime import datetime

### Variables init ###############################################################################
list_state_init: list[tuple[dict[str, Any], dict[str, Any]]] = [
    (
        {
            # empty
        },
        {
            "a": {
                "streak": 0,
                "last_completed": None,
                "done_today": False,
            },
            "b": {
                "streak": 0,
                "last_completed": None,
                "done_today": False,
            },
            "c": {
                "streak": 0,
                "last_completed": None,
                "done_today": False,
            },
        },
    ),
    (
        {
            "b": {
                "streak": 13,
                "last_completed": "12-12-2025",
                "done_today": False,
            },
            "c": {
                "streak": 45,
                "last_completed": "12-12-2025",
                "done_today": False,
            },
        },
        {
            "a": {
                "streak": 0,
                "last_completed": None,
                "done_today": False,
            },
            "b": {
                "streak": 13,
                "last_completed": "12-12-2025",
                "done_today": False,
            },
            "c": {
                "streak": 45,
                "last_completed": "12-12-2025",
                "done_today": False,
            },
        },
    ),
]

list_diff_dates: list[tuple[str, str, int]] = [
    ("2026-04-01", "2026-04-10", 9),
    ("2026-04-01", "2026-05-01", 30),
    ("2025-12-31", "2026-01-05", 5),
    ("1", "0", 0),
    ("56", "2026-04-10", 0),
]

maintenance_jsons: list[tuple[dict[str, Any], dict[str, Any], int]] = [
    # ({input},
    # {expected output}),
    # day_diff
    (
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-02",
                "done_today": True,
            }
        },
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-02",
                "done_today": True,
            }
        },
        0,
    ),
    (
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-08",
                "done_today": False,
            }
        },
        {
            "SPF applied": {
                "streak": 0,
                "last_completed": "2026-04-08",
                "done_today": False,
            }
        },
        10,
    ),
    (
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-10",
                "done_today": True,
            }
        },
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-10",
                "done_today": False,
            }
        },
        1,
    ),
    (
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-10",
                "done_today": True,
            }
        },
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-10",
                "done_today": False,
            }
        },
        2,
    ),
]

mark_done_jsons: list[tuple[dict[str, Any], dict[str, Any]]] = [
    (
        {
            "SPF applied": {
                "streak": 12,
                "last_completed": "2026-04-02",
                "done_today": False,
            }
        },
        {
            "SPF applied": {
                "streak": 13,
                "last_completed": "2026-04-03",
                "done_today": True,
            }
        },
    ),
    (
        {
            "SPF applied": {
                "streak": 8,
                "last_completed": "2026-04-02",
                "done_today": True,
            }
        },
        {
            "SPF applied": {
                "streak": 8,
                "last_completed": "2026-04-02",
                "done_today": True,
            }
        },
    ),
]

list_of_datetime: list[tuple[Any, bool]] = [
    (datetime(2026, 4, 20, 9, 0, 0), True),  # Thursday 9am
    (datetime(2026, 4, 25, 15, 0, 0), True),  # Saturday 3pm
    (datetime(2026, 4, 14, 1, 0, 0), False),  # Tuesday 1am
]


### TESTS ########################################################################################


@pytest.mark.parametrize("input, expected", list_state_init)
def test_state_init(mocker: Any, input: dict[str, Any], expected: dict[str, Any]):
    mocker.patch("good_start_habits.habits.HABITS", new=["a", "b", "c"])
    mocker.patch("good_start_habits.habits.save_state")

    state_init(input)
    assert input == expected


@pytest.mark.parametrize("previous_date, current_date, expected", list_diff_dates)
def test_day_diff(previous_date: str, current_date: str, expected: int):
    assert day_diff(previous_date, current_date) == expected


@pytest.mark.parametrize("input, expected, day_diff", maintenance_jsons)
def test_daily_maintenance(
    mocker: Any, input: dict[str, Any], expected: dict[str, Any], day_diff: int
):
    mocker.patch("good_start_habits.habits.day_diff", return_value=day_diff)
    mocker.patch("good_start_habits.habits.save_state")

    daily_maintenance(input)
    assert input == expected


@pytest.mark.parametrize("input, expected", mark_done_jsons)
def test_mark_done(mocker: Any, input: dict[str, Any], expected: dict[str, Any]):
    mock_date = mocker.patch("good_start_habits.habits.date")
    mock_date.today.return_value = "2026-04-03"
    mocker.patch("good_start_habits.habits.save_state")

    mark_done(input, "SPF applied")
    assert input == expected


@pytest.mark.parametrize("input, expected", list_of_datetime)
def test_check_current_datetime(mocker: Any, input: Any, expected: bool):
    TEST_ACTIVE_TIMES = {
        "Monday": ("08:00:00", "21:00:00"),
        "Tuesday": ("08:00:00", "21:00:00"),
        "Thursday": ("08:00:00", "21:00:00"),
        "Saturday": ("08:00:00", "21:00:00"),
    }
    mocker.patch("good_start_habits.habits.ACTIVE_TIMES", TEST_ACTIVE_TIMES)

    mock_datetime = mocker.patch("good_start_habits.habits.datetime")
    mock_datetime.now.return_value = input  # m,d, h,m,s

    bool = check_current_datetime()
    assert bool == expected
