import sqlite3
from flask import g
from good_start_habits.config import BASE_INCOME, DEFAULT_EXTRA_INCOME, HABITS


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


def init_budget_settings(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_settings (
            year         INTEGER NOT NULL,
            month        INTEGER NOT NULL,
            base_income  REAL    NOT NULL DEFAULT 2440.0,
            extra_income REAL    NOT NULL DEFAULT 100.0,
            notes        TEXT,
            PRIMARY KEY (year, month)
        )
        """
    )


def get_budget_settings(db: sqlite3.Connection, year: int, month: int) -> dict:
    row = db.execute(
        "SELECT base_income, extra_income, notes FROM budget_settings"
        " WHERE year=? AND month=?",
        (year, month),
    ).fetchone()
    if row:
        return {"base_income": row[0], "extra_income": row[1], "notes": row[2] or ""}
    return {
        "base_income": BASE_INCOME,
        "extra_income": DEFAULT_EXTRA_INCOME,
        "notes": "",
    }


def save_budget_settings(
    db: sqlite3.Connection,
    year: int,
    month: int,
    base_income: float,
    extra_income: float,
    notes: str = "",
) -> None:
    db.execute(
        """
        INSERT INTO budget_settings (year, month, base_income, extra_income, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(year, month) DO UPDATE SET
            base_income  = excluded.base_income,
            extra_income = excluded.extra_income,
            notes        = excluded.notes
        """,
        (year, month, base_income, extra_income, notes),
    )
    db.commit()


def get_savings_baselines(
    db: sqlite3.Connection, year: int, month: int
) -> dict[str, float]:
    """Return the most recent baseline for each account, up to (year, month).

    Falls back to default_balance from config if no row exists in the DB.
    """
    from good_start_habits.config import SAVINGS_ACCOUNTS

    result = {acc["name"]: acc.get("default_balance", 0.0) for acc in SAVINGS_ACCOUNTS}
    rows = db.execute(
        """
        SELECT s.account, s.balance
        FROM savings_baseline s
        JOIN (
            SELECT account, MAX(year * 100 + month) AS max_ym
            FROM savings_baseline
            WHERE year * 100 + month <= ?
            GROUP BY account
        ) m ON s.account = m.account
           AND s.year * 100 + s.month = m.max_ym
        """,
        (year * 100 + month,),
    ).fetchall()
    for row in rows:
        result[row[0]] = row[1]
    return result


def save_savings_baseline(
    db: sqlite3.Connection, account: str, year: int, month: int, balance: float
) -> None:
    db.execute(
        """
        INSERT INTO savings_baseline (account, year, month, balance)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(account, year, month) DO UPDATE SET balance = excluded.balance
        """,
        (account, year, month, balance),
    )
    db.commit()


def init_db():
    """Create all tables if they do not exist and seed habit rows."""
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
    init_budget_settings(db)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS category_overrides (
            description_lower TEXT PRIMARY KEY,
            category          TEXT NOT NULL,
            created_at        TEXT DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_baseline (
            account  TEXT    NOT NULL,
            year     INTEGER NOT NULL,
            month    INTEGER NOT NULL,
            balance  REAL    NOT NULL DEFAULT 0.0,
            PRIMARY KEY (account, year, month)
        )
        """
    )
    populate_habits()
    db.commit()
