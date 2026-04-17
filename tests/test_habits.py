from good_start_habits.habits import day_diff, daily_maintenance, mark_done
import pytest
from typing import Any

### Variables init ###############################################################################
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

### TESTS ########################################################################################


# COMPLETED
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


# TODO
json: list[tuple[dict[str, Any], dict[str, Any]]] = []


@pytest.mark.parametrize(
    "input, expected, day_diff", json
)  # new list of jsons with updated streaks
def test_mark_done(
    mocker: Any, input: dict[str, Any], expected: dict[str, Any], day_diff: int
):
    mock_date = mocker.patch("good_start_habits.habits.date")
    mock_date.today.return_value = "2026-04-02"
    mocker.patch("good_start_habits.habits.save_state")

    mark_done(input, "SPF applied")
    assert input == expected
