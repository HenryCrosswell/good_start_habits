import sqlite3
from typing import Any
from flask import Flask
from good_start_habits.db import get_db, init_db, init_tl_tables, populate_habits
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

    # second call must be idempotent
    populate_habits()
    rows = test_db.execute("SELECT name FROM habits ORDER BY name").fetchall()
    assert rows == [(h,) for h in sorted(habits)]


# ---------------------------------------------------------------------------
# init_tl_tables
# ---------------------------------------------------------------------------


def test_init_tl_tables_creates_both_tables():
    db = sqlite3.connect(":memory:")
    init_tl_tables(db)
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "tl_tokens" in tables
    assert "oauth_state" in tables


def test_init_tl_tables_is_idempotent():
    db = sqlite3.connect(":memory:")
    init_tl_tables(db)
    init_tl_tables(db)  # second call must not raise


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_all_tables(mocker: Any):
    app = Flask(__name__)
    db = sqlite3.connect(":memory:")
    mocker.patch("good_start_habits.db.sqlite3").connect.return_value = db
    mocker.patch("good_start_habits.db.HABITS", ["SPF applied"])
    with app.app_context():
        init_db()
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "habits" in tables
    assert "tl_tokens" in tables
    assert "oauth_state" in tables
