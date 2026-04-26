import sqlite3
from flask import g
from good_start_habits.config import HABITS


def get_db():
    """Return the per-request SQLite connection, creating it if needed.

    Uses Flask's ``g`` object so the same connection is reused within a
    single request and torn down automatically when the request ends.

    Returns:
        sqlite3.Connection: Open connection to ``dashboard.db``.
    """
    db = getattr(g, "database", None)
    if db is None:
        db = g.database = sqlite3.connect("dashboard.db")
    return db


def populate_habits():
    """Insert any habits from config that are not already in the database.

    Uses ``INSERT OR IGNORE`` so existing rows are left untouched.
    Opens its own connection because this is called during app setup,
    outside of a Flask request context.
    """
    con = sqlite3.connect("dashboard.db")
    cur = con.cursor()
    for habit in HABITS:
        cur.execute(
            """INSERT OR IGNORE INTO habits (
        name,
        last_completed)
        VALUES(?,?)
        """,
            (habit, None),
        )
    con.commit()


def init_tl_tables(db: sqlite3.Connection) -> None:
    """Create TrueLayer token and OAuth state tables if they don't exist."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tl_tokens (
            provider      TEXT PRIMARY KEY,
            access_token  TEXT NOT NULL,
            refresh_token TEXT,
            expires_at    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_state (
            state         TEXT PRIMARY KEY,
            provider_hint TEXT NOT NULL,
            code_verifier TEXT NOT NULL,
            expires_at    TEXT NOT NULL
        )
        """
    )


def init_db():
    """Create the ``habits`` table if it does not exist and seed habit rows.

    Safe to call on every app start — the ``CREATE TABLE IF NOT EXISTS``
    guard and ``INSERT OR IGNORE`` in :func:`populate_habits` make it
    idempotent.
    """
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
    init_tl_tables(db)
    populate_habits()
    db.commit()
