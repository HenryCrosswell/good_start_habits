import sqlite3
from flask import g


def get_db():
    db = getattr(g, "database", None)
    if db is None:
        db = g.database = sqlite3.connect("dashboard.db")
    return db


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS habits (
        name           TEXT PRIMARY KEY,
        streak         INTEGER NOT NULL DEFAULT 0,
        last_completed TEXT,
        done_today     INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    db.commit()


def close_db(e=None):
    db = g.pop("database", None)
    if db is not None:
        db.close()
