import sqlite3
from typing import Any
from flask import Flask
from good_start_habits.db import get_db, populate_habits
import pytest

### Variables init ###############################################################################


@pytest.fixture()
def test_db():
    test_db = sqlite3.connect(":memory:")
    test_db.execute(
        """
        CREATE TABLE IF NOT EXISTS habits (
        name           TEXT PRIMARY KEY,
        streak         INTEGER NOT NULL DEFAULT 0,
        last_completed TEXT,
        done_today     INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    test_db.commit()
    return test_db


habits = ["Vitamins & Omega-3", "Log meal"]

### TESTS ########################################################################################


def test_get_db(mocker: Any):
    app = Flask(__name__)
    mocker.patch("good_start_habits.db.sqlite3").connect.return_value = sqlite3.connect(
        ":memory:"
    )
    with app.app_context():
        db = get_db()
        assert type(db) is sqlite3.Connection
        db1 = get_db()
        assert db is db1


def test_populate_habits(mocker: Any, test_db: sqlite3.Connection):
    mocker.patch("good_start_habits.db.sqlite3").connect.return_value = test_db
    mocker.patch("good_start_habits.db.HABITS", habits)

    populate_habits()
    rows = test_db.execute("SELECT name FROM habits ORDER BY name").fetchall()
    assert rows == [(h,) for h in sorted(habits)]

    populate_habits()
    rows = test_db.execute("SELECT name FROM habits ORDER BY name").fetchall()
    assert rows == [(h,) for h in sorted(habits)]
