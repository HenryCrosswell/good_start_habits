from good_start_habits.habits import (
    day_diff,
    daily_maintenance,
    mark_done,
    check_current_datetime,
)
import pytest
from typing import Any
from datetime import datetime
import sqlite3


### Variables init ###############################################################################


@pytest.fixture
def db():
    con = sqlite3.connect(":memory:")
    con.execute("""
        CREATE TABLE habits (
            name           TEXT PRIMARY KEY,
            streak         INTEGER NOT NULL DEFAULT 0,
            last_completed TEXT,
            done_today     INTEGER NOT NULL DEFAULT 0
        )
    """)
    con.commit()
    yield con
    con.close()


list_diff_dates: list[tuple[str, str, int]] = [
    ("2026-04-01", "2026-04-10", 9),
    ("2026-04-01", "2026-05-01", 30),
    ("2025-12-31", "2026-01-05", 5),
    ("1", "0", 0),
    ("56", "2026-04-10", 0),
]

SeedRow = tuple[str, int, str, int]
ExpectedRow = tuple[int, str, int]
maintenance_jsons: list[tuple[SeedRow, ExpectedRow, int]] = [
    (("SPF applied", 12, "2026-04-02", 1), (12, "2026-04-02", 1), 0),
    (("SPF applied", 12, "2026-04-08", 0), (0, "2026-04-08", 0), 10),
    (("SPF applied", 12, "2026-04-10", 1), (12, "2026-04-10", 0), 1),
    (("SPF applied", 12, "2026-04-10", 1), (12, "2026-04-10", 0), 2),
]

mark_done_rows: list[tuple[SeedRow, ExpectedRow, bool]] = [
    # (seed: name, streak, last_completed, done_today), (expected: streak, last_completed, done_today), undo
    (
        ("SPF applied", 12, "2026-04-02", 0),
        (13, "2026-04-03", 1),
        False,
    ),  # not done — should complete
    (
        ("SPF applied", 8, "2026-04-02", 1),
        (8, "2026-04-02", 1),
        False,
    ),  # already done — no change
    (
        ("SPF applied", 12, "2026-04-03", 1),
        (11, "2026-04-03", 0),
        True,
    ),  # undo done habit — decrements streak
    (
        ("SPF applied", 5, "2026-04-03", 0),
        (5, "2026-04-03", 0),
        True,
    ),  # undo not-done habit — no change
]

list_of_datetime: list[tuple[Any, bool]] = [
    (datetime(2026, 4, 20, 9, 0, 0), True),  # Thursday 9am
    (datetime(2026, 4, 25, 15, 0, 0), True),  # Saturday 3pm
    (datetime(2026, 4, 14, 1, 0, 0), False),  # Tuesday 1am
]


### TESTS ########################################################################################


@pytest.mark.parametrize("previous_date, current_date, expected", list_diff_dates)
def test_day_diff(previous_date: str, current_date: str, expected: int):
    assert day_diff(previous_date, current_date) == expected


@pytest.mark.parametrize("seed, expected, day_diff", maintenance_jsons)
def test_daily_maintenance(
    mocker: Any,
    db: sqlite3.Connection,
    seed: SeedRow,
    expected: ExpectedRow,
    day_diff: int,
):
    db.execute(
        "INSERT INTO habits (name, streak, last_completed, done_today) VALUES (?,?,?,?)",
        seed,
    )
    db.commit()
    mocker.patch("good_start_habits.habits.sqlite3").connect.return_value = db
    mocker.patch("good_start_habits.habits.day_diff", return_value=day_diff)
    daily_maintenance(db)

    row = db.execute(
        "SELECT streak, last_completed, done_today FROM habits WHERE name = 'SPF applied'"
    ).fetchone()
    assert row == expected


@pytest.mark.parametrize("seed, expected, undo", mark_done_rows)
def test_mark_done(
    mocker: Any,
    db: sqlite3.Connection,
    seed: SeedRow,
    expected: ExpectedRow,
    undo: bool,
):
    db.execute(
        "INSERT INTO habits (name, streak, last_completed, done_today) VALUES (?,?,?,?)",
        seed,
    )
    db.commit()
    mocker.patch("good_start_habits.habits.sqlite3").connect.return_value = db
    mock_date = mocker.patch("good_start_habits.habits.date")
    mock_date.today.return_value = "2026-04-03"

    mark_done(db, "SPF applied", undo)

    row = db.execute(
        "SELECT streak, last_completed, done_today FROM habits WHERE name = 'SPF applied'"
    ).fetchone()
    assert row == expected


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
