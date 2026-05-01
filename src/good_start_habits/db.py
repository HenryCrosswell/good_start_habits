import os
import sqlite3
from flask import g
from good_start_habits.config import BASE_INCOME, DEFAULT_EXTRA_INCOME, HABITS

DB_PATH: str = os.environ.get("DB_PATH", "dashboard.db")


def get_db():
    db = getattr(g, "database", None)
    if db is None:
        db = g.database = sqlite3.connect(DB_PATH)
    return db


def populate_habits():
    con = sqlite3.connect(DB_PATH)
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


def init_garmin_tables(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_activities (
            activity_id       INTEGER PRIMARY KEY,
            activity_date     TEXT    NOT NULL,
            name              TEXT    NOT NULL DEFAULT '',
            distance_meters   REAL,
            duration_seconds  REAL,
            avg_hr_bpm        REAL,
            max_hr_bpm        REAL,
            calories          INTEGER,
            run_distance_m    REAL,
            run_duration_s    REAL,
            ef                REAL,
            run_pace_s_per_km REAL,
            avg_cadence_spm   REAL,
            fetched_at        TEXT DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_summaries (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at     TEXT NOT NULL,
            last_activity_id INTEGER,
            summary_type     TEXT NOT NULL DEFAULT 'activity',
            period_key       TEXT,
            summary          TEXT NOT NULL
        )
        """
    )
    # Migrate pre-existing tables that lack the new columns
    for col, defn in [
        ("summary_type", "TEXT NOT NULL DEFAULT 'activity'"),
        ("period_key", "TEXT"),
    ]:
        try:
            db.execute(f"ALTER TABLE garmin_summaries ADD COLUMN {col} {defn}")
        except Exception:
            pass  # column already exists
    try:
        db.execute("ALTER TABLE garmin_activities ADD COLUMN avg_cadence_spm REAL")
    except Exception:
        pass  # column already exists
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_chat_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            asked_date TEXT NOT NULL,
            question   TEXT NOT NULL,
            response   TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS garmin_fitness_cache (
            fetched_date TEXT PRIMARY KEY,
            data         TEXT NOT NULL,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
        """
    )


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
    init_garmin_tables(db)
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
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS sinking_fund_overrides (
            description_lower TEXT PRIMARY KEY,
            created_at        TEXT DEFAULT (datetime('now'))
        )
        """
    )
    populate_habits()
    db.commit()
