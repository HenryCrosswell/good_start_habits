import sqlite3
from flask import g


def init_db():
    # Create a table
    con = sqlite3.connect("dashboard.db")
    cur = con.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS habits (
    name          TEXT PRIMARY KEY,
    streak        INTEGER NOT NULL DEFAULT 0,
    last_completed TEXT,
    done_today    INTEGER NOT NULL DEFAULT 0
  """
    )


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect("dashboard.db")
    return db


def close_db(e: BaseException):
    db = g.pop("db", None)
    if db is not None:
        db.close()
