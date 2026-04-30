"""Tests for good_start_habits.garmin."""

import sqlite3
from unittest.mock import MagicMock

import pytest

from good_start_habits.garmin import (
    _active_laps_stats,
    _indicator,
    _pace_secs,
    _pace_str,
    build_ef_chart,
    compute_ef,
    generate_summary,
    get_all_activities,
    get_latest_run_stats,
    sync_activities,
)


# ---------------------------------------------------------------------------
# Fixture: in-memory DB with garmin tables
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE garmin_activities (
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
            fetched_at        TEXT DEFAULT (datetime('now'))
        )
        """
    )
    con.execute(
        """
        CREATE TABLE garmin_summaries (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at     TEXT NOT NULL,
            last_activity_id INTEGER,
            summary          TEXT NOT NULL
        )
        """
    )
    con.commit()
    yield con
    con.close()


def _insert_activity(db, **kwargs):
    defaults = {
        "activity_id": 1,
        "activity_date": "2026-04-01",
        "name": "Test Run",
        "distance_meters": 5000.0,
        "duration_seconds": 1800.0,
        "avg_hr_bpm": 150.0,
        "max_hr_bpm": 175.0,
        "calories": 400,
        "run_distance_m": 4000.0,
        "run_duration_s": 1200.0,
        "ef": 0.0800,
        "run_pace_s_per_km": 300.0,
    }
    defaults.update(kwargs)
    db.execute(
        """
        INSERT INTO garmin_activities
            (activity_id, activity_date, name, distance_meters, duration_seconds,
             avg_hr_bpm, max_hr_bpm, calories, run_distance_m, run_duration_s,
             ef, run_pace_s_per_km)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        list(defaults.values()),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "speed_mps, avg_hr, expected",
    [
        (3.264, 165.0, round((3.264 * 3.6) / 165.0, 5)),  # real-world 5:06/km example
        (3.0, 150.0, round((3.0 * 3.6) / 150.0, 5)),
        (2.5, 0.0, None),  # zero HR → None
        (2.5, -1.0, None),  # negative HR → None
    ],
)
def test_compute_ef(speed_mps, avg_hr, expected):
    assert compute_ef(speed_mps, avg_hr) == expected


def test_compute_ef_matches_user_example():
    # 5:06/km run pace → 306 s/km → 1000/306 m/s ≈ 3.268 m/s
    # EF = (3.268 * 3.6) / 165 ≈ 0.0713
    ef = compute_ef(1000 / 306, 165.0)
    assert ef is not None
    assert 0.070 < ef < 0.073


@pytest.mark.parametrize(
    "sec_per_km, expected",
    [
        (306.0, "5:06"),
        (394.0, "6:34"),
        (300.0, "5:00"),
        (360.0, "6:00"),
    ],
)
def test_pace_str(sec_per_km, expected):
    assert _pace_str(sec_per_km) == expected


@pytest.mark.parametrize(
    "pace_str, expected",
    [
        ("5:06", 306),
        ("6:34", 394),
        ("5:00", 300),
        (None, None),
        ("", None),
    ],
)
def test_pace_secs(pace_str, expected):
    assert _pace_secs(pace_str) == expected


def test_active_laps_stats_mixed():
    laps = [
        {"distance": 400.0, "duration": 120.0, "intensityType": "ACTIVE"},
        {"distance": 140.0, "duration": 90.0, "intensityType": "REST"},
        {"distance": 400.0, "duration": 122.0, "intensityType": "ACTIVE"},
        {"distance": 130.0, "duration": 90.0, "intensityType": "COOLDOWN"},
    ]
    dist, dur = _active_laps_stats(laps)
    assert dist == 800.0
    assert dur == 242.0


def test_active_laps_stats_all_rest():
    laps = [{"distance": 100.0, "duration": 60.0, "intensityType": "REST"}]
    assert _active_laps_stats(laps) == (None, None)


def test_active_laps_stats_empty():
    assert _active_laps_stats([]) == (None, None)


def test_active_laps_stats_single_active():
    laps = [{"distance": 400.0, "duration": 121.8, "intensityType": "ACTIVE"}]
    dist, dur = _active_laps_stats(laps)
    assert dist == 400.0
    assert dur == 121.8


@pytest.mark.parametrize(
    "curr, prev, higher_is_better, arrow, good_expected",
    [
        (0.072, 0.068, True, "▲", True),  # EF improved
        (0.065, 0.070, True, "▼", False),  # EF declined
        (300.0, 320.0, False, "▼", True),  # pace improved (lower)
        (175.0, 165.0, False, "▲", False),  # HR worsened (higher)
        (5.0, 5.0, True, "—", None),  # unchanged
    ],
)
def test_indicator(curr, prev, higher_is_better, arrow, good_expected):
    result = _indicator(curr, prev, higher_is_better=higher_is_better)
    assert result["arrow"] == arrow
    assert result["good"] == good_expected


def test_indicator_none_prev():
    result = _indicator(0.072, None)
    assert result["pct"] is None
    assert result["arrow"] == ""


# ---------------------------------------------------------------------------
# DB-backed function tests
# ---------------------------------------------------------------------------


def test_get_all_activities_empty(db):
    assert get_all_activities(db) == []


def test_get_all_activities_with_data(db):
    _insert_activity(db, activity_id=1, activity_date="2026-01-10", ef=0.075)
    _insert_activity(db, activity_id=2, activity_date="2026-02-15", ef=0.080)

    result = get_all_activities(db)
    assert len(result) == 2
    assert result[0]["date"] == "2026-01-10"  # oldest first
    assert result[1]["date"] == "2026-02-15"
    assert result[0]["ef"] == 0.075
    assert result[0]["distance_km"] == 5.0
    assert result[0]["run_pace"] == "5:00"


def test_get_latest_run_stats_single_run(db):
    _insert_activity(db, activity_id=1, activity_date="2026-04-30", ef=0.071)
    activities = get_all_activities(db)
    stats = get_latest_run_stats(activities)

    assert stats is not None
    assert stats["ef"] == 0.071
    assert stats["ef_ind"]["pct"] is None  # no previous to compare


def test_get_latest_run_stats_comparison(db):
    _insert_activity(
        db, activity_id=1, activity_date="2026-04-01", ef=0.068, avg_hr_bpm=165.0
    )
    _insert_activity(
        db, activity_id=2, activity_date="2026-04-30", ef=0.072, avg_hr_bpm=160.0
    )
    activities = get_all_activities(db)
    stats = get_latest_run_stats(activities)

    assert stats["ef"] == 0.072
    # EF improved → up arrow, good
    assert stats["ef_ind"]["arrow"] == "▲"
    assert stats["ef_ind"]["good"] is True
    # HR lower → down arrow, good
    assert stats["hr_ind"]["arrow"] == "▼"
    assert stats["hr_ind"]["good"] is True


def test_get_latest_run_stats_no_ef_data(db):
    _insert_activity(db, activity_id=1, ef=None)
    activities = get_all_activities(db)
    assert get_latest_run_stats(activities) is None


def test_build_ef_chart_empty_returns_empty_string(db):
    assert build_ef_chart([]) == ""


def test_build_ef_chart_returns_plotly_json(db):
    import json

    _insert_activity(db, activity_id=1, activity_date="2026-01-10", ef=0.068)
    _insert_activity(db, activity_id=2, activity_date="2026-02-01", ef=0.071)
    activities = get_all_activities(db)
    chart_json = build_ef_chart(activities)

    assert chart_json != ""
    parsed = json.loads(chart_json)
    assert "data" in parsed
    assert "layout" in parsed
    # First trace is the per-run EF scatter
    assert any("EF per run" in str(t.get("name", "")) for t in parsed["data"])


# ---------------------------------------------------------------------------
# sync_activities tests (mocked client)
# ---------------------------------------------------------------------------


def _make_mock_client(activities=None, splits=None):
    client = MagicMock()
    client.get_activities_by_date.return_value = activities or []
    client.get_activity_splits.return_value = {"lapDTOs": splits or []}
    return client


@pytest.fixture
def mock_client(mocker):
    client = _make_mock_client()
    mocker.patch("good_start_habits.garmin._get_client", return_value=client)
    return client


def test_sync_skips_missing_hr(mock_client, db):
    mock_client.get_activities_by_date.return_value = [
        {
            "activityId": 1,
            "distance": 5000.0,
            "averageHR": None,
            "startTimeLocal": "2026-04-01 09:00:00",
        },
    ]
    assert sync_activities(db) == 0
    assert db.execute("SELECT COUNT(*) FROM garmin_activities").fetchone()[0] == 0


def test_sync_skips_missing_distance(mock_client, db):
    mock_client.get_activities_by_date.return_value = [
        {
            "activityId": 1,
            "distance": 0,
            "averageHR": 150.0,
            "startTimeLocal": "2026-04-01 09:00:00",
        },
    ]
    assert sync_activities(db) == 0


def test_sync_skips_already_stored(mock_client, db):
    _insert_activity(db, activity_id=99)
    mock_client.get_activities_by_date.return_value = [
        {
            "activityId": 99,
            "distance": 5000.0,
            "averageHR": 150.0,
            "startTimeLocal": "2026-04-01 09:00:00",
        },
    ]
    assert sync_activities(db) == 0


def test_sync_inserts_valid_activity(mocker, db):
    laps = [
        {"distance": 400.0, "duration": 121.8, "intensityType": "ACTIVE"},
        {"distance": 140.0, "duration": 90.0, "intensityType": "REST"},
    ]
    client = _make_mock_client(
        activities=[
            {
                "activityId": 42,
                "activityName": "St Albans Running",
                "startTimeLocal": "2026-04-30 12:16:25",
                "distance": 4276.0,
                "duration": 1686.0,
                "averageHR": 165.0,
                "maxHR": 192.0,
                "calories": 398,
            }
        ],
        splits=laps,
    )
    mocker.patch("good_start_habits.garmin._get_client", return_value=client)
    mocker.patch("good_start_habits.garmin.time.sleep")

    added = sync_activities(db)
    assert added == 1

    row = db.execute(
        "SELECT activity_id, ef, run_distance_m, run_pace_s_per_km FROM garmin_activities WHERE activity_id = 42"
    ).fetchone()
    assert row is not None
    assert row[0] == 42
    assert row[1] is not None  # EF computed
    assert row[2] == 400.0  # ACTIVE lap distance only


def test_sync_falls_back_to_total_speed_on_splits_error(mocker, db):
    client = _make_mock_client(
        activities=[
            {
                "activityId": 7,
                "activityName": "Morning Run",
                "startTimeLocal": "2026-04-01 07:00:00",
                "distance": 5000.0,
                "duration": 1500.0,
                "averageHR": 150.0,
                "maxHR": 170.0,
                "calories": 300,
            }
        ]
    )
    client.get_activity_splits.side_effect = RuntimeError("network error")
    mocker.patch("good_start_habits.garmin._get_client", return_value=client)
    mocker.patch("good_start_habits.garmin.time.sleep")

    added = sync_activities(db)
    assert added == 1
    row = db.execute(
        "SELECT ef FROM garmin_activities WHERE activity_id = 7"
    ).fetchone()
    assert row[0] is not None  # fallback EF from total speed


def test_sync_returns_zero_when_client_unavailable(mocker, db):
    mocker.patch("good_start_habits.garmin._get_client", return_value=None)
    assert sync_activities(db) == 0


# ---------------------------------------------------------------------------
# generate_summary tests
# ---------------------------------------------------------------------------


def test_generate_summary_no_api_key(monkeypatch, db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _insert_activity(db)
    activities = get_all_activities(db)
    assert generate_summary(db, activities) == ""


def test_generate_summary_uses_cache(monkeypatch, db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _insert_activity(db, activity_id=1)
    # Pre-cache a summary for activity_id=1
    db.execute(
        "INSERT INTO garmin_summaries (generated_at, last_activity_id, summary)"
        " VALUES ('2026-04-30', 1, 'Great work on your run!')"
    )
    db.commit()

    activities = get_all_activities(db)
    result = generate_summary(db, activities)
    assert result == "Great work on your run!"


def test_generate_summary_empty_activities(db):
    assert generate_summary(db, []) == ""


def test_generate_summary_no_ef_activities(db):
    _insert_activity(db, ef=None)
    activities = get_all_activities(db)
    assert generate_summary(db, activities) == ""
