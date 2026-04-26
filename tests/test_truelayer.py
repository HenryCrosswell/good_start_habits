"""Tests for TrueLayer helpers that don't require HTTP calls."""

import hashlib
import base64
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from good_start_habits.truelayer import (
    _b64url,
    _make_pkce_pair,
    disconnect,
    get_connection_status,
    get_valid_token,
    save_tokens,
)


# ---------------------------------------------------------------------------
# Fixture: in-memory DB with tl_tokens schema
# ---------------------------------------------------------------------------


@pytest.fixture
def tl_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE tl_tokens (
            provider      TEXT PRIMARY KEY,
            access_token  TEXT NOT NULL,
            refresh_token TEXT,
            expires_at    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.commit()
    return con


def _future(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# _b64url
# ---------------------------------------------------------------------------


class TestB64url:
    def test_no_padding(self):
        result = _b64url(b"hello")
        assert "=" not in result

    def test_url_safe_characters_only(self):
        result = _b64url(bytes(range(256)))
        assert "+" not in result
        assert "/" not in result

    def test_roundtrip(self):
        data = b"\xff\xfe\xfd\xfc"
        encoded = _b64url(data)
        # Re-add padding and decode
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(encoded + padding)
        assert decoded == data


# ---------------------------------------------------------------------------
# _make_pkce_pair
# ---------------------------------------------------------------------------


class TestMakePkcePair:
    def test_challenge_derives_from_verifier(self):
        verifier, challenge = _make_pkce_pair()
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge == expected

    def test_pairs_are_unique(self):
        v1, _ = _make_pkce_pair()
        v2, _ = _make_pkce_pair()
        assert v1 != v2

    def test_verifier_is_non_empty_string(self):
        verifier, challenge = _make_pkce_pair()
        assert isinstance(verifier, str) and len(verifier) > 0
        assert isinstance(challenge, str) and len(challenge) > 0


# ---------------------------------------------------------------------------
# save_tokens
# ---------------------------------------------------------------------------


class TestSaveTokens:
    def test_inserts_new_row(self, tl_db: sqlite3.Connection):
        save_tokens(
            tl_db,
            "monzo",
            {
                "access_token": "tok123",
                "refresh_token": "ref456",
                "expires_in": 3600,
            },
        )
        row = tl_db.execute(
            "SELECT provider, access_token, refresh_token FROM tl_tokens WHERE provider='monzo'"
        ).fetchone()
        assert row == ("monzo", "tok123", "ref456")

    def test_upserts_on_duplicate_provider(self, tl_db: sqlite3.Connection):
        save_tokens(
            tl_db,
            "monzo",
            {"access_token": "old", "refresh_token": "r1", "expires_in": 3600},
        )
        save_tokens(
            tl_db,
            "monzo",
            {"access_token": "new", "refresh_token": "r2", "expires_in": 3600},
        )
        row = tl_db.execute(
            "SELECT access_token FROM tl_tokens WHERE provider='monzo'"
        ).fetchone()
        assert row[0] == "new"

    def test_preserves_existing_refresh_token_when_omitted(
        self, tl_db: sqlite3.Connection
    ):
        save_tokens(
            tl_db,
            "monzo",
            {"access_token": "tok", "refresh_token": "keep_me", "expires_in": 3600},
        )
        save_tokens(tl_db, "monzo", {"access_token": "tok2", "expires_in": 3600})
        row = tl_db.execute(
            "SELECT refresh_token FROM tl_tokens WHERE provider='monzo'"
        ).fetchone()
        assert row[0] == "keep_me"

    def test_defaults_expires_in_to_3600(self, tl_db: sqlite3.Connection):
        before = datetime.now(timezone.utc)
        save_tokens(tl_db, "monzo", {"access_token": "tok"})
        expires_at_str = tl_db.execute(
            "SELECT expires_at FROM tl_tokens WHERE provider='monzo'"
        ).fetchone()[0]
        expires_at = datetime.fromisoformat(expires_at_str)
        assert expires_at > before + timedelta(minutes=59)


# ---------------------------------------------------------------------------
# get_valid_token
# ---------------------------------------------------------------------------


class TestGetValidToken:
    def test_returns_none_when_no_row(self, tl_db: sqlite3.Connection):
        assert get_valid_token(tl_db, "monzo") is None

    def test_returns_token_when_not_near_expiry(self, tl_db: sqlite3.Connection):
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "fresh_tok", "ref", _future(1)),
        )
        tl_db.commit()
        assert get_valid_token(tl_db, "monzo") == "fresh_tok"

    def test_returns_none_when_expired_and_no_refresh_token(
        self, tl_db: sqlite3.Connection
    ):
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "expired_tok", None, _past(1)),
        )
        tl_db.commit()
        assert get_valid_token(tl_db, "monzo") is None

    def test_refreshes_when_within_buffer(self, mocker: Any, tl_db: sqlite3.Connection):
        near_expiry = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "old_tok", "ref_tok", near_expiry),
        )
        tl_db.commit()
        mocker.patch(
            "good_start_habits.truelayer._do_refresh",
            return_value={
                "access_token": "new_tok",
                "refresh_token": "new_ref",
                "expires_in": 3600,
            },
        )
        result = get_valid_token(tl_db, "monzo")
        assert result == "new_tok"

    def test_returns_none_when_refresh_raises(
        self, mocker: Any, tl_db: sqlite3.Connection
    ):
        import requests

        near_expiry = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "old_tok", "ref_tok", near_expiry),
        )
        tl_db.commit()
        mocker.patch(
            "good_start_habits.truelayer._do_refresh",
            side_effect=requests.RequestException("network error"),
        )
        assert get_valid_token(tl_db, "monzo") is None


# ---------------------------------------------------------------------------
# get_connection_status
# ---------------------------------------------------------------------------


class TestGetConnectionStatus:
    def test_all_disconnected_when_empty(self, tl_db: sqlite3.Connection):
        status = get_connection_status(tl_db)
        assert status == {
            "monzo": "disconnected",
            "nationwide": "disconnected",
            "amex": "disconnected",
        }

    def test_connected_provider_shows_connected(self, tl_db: sqlite3.Connection):
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "tok", "ref", _future()),
        )
        tl_db.commit()
        status = get_connection_status(tl_db)
        assert status["monzo"] == "connected"
        assert status["nationwide"] == "disconnected"
        assert status["amex"] == "disconnected"

    def test_all_connected(self, tl_db: sqlite3.Connection):
        for provider in ("monzo", "nationwide", "amex"):
            tl_db.execute(
                "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
                (provider, "tok", "ref", _future()),
            )
        tl_db.commit()
        status = get_connection_status(tl_db)
        assert all(v == "connected" for v in status.values())


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    def test_removes_token_row(self, tl_db: sqlite3.Connection):
        tl_db.execute(
            "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("monzo", "tok", "ref", _future()),
        )
        tl_db.commit()
        disconnect(tl_db, "monzo")
        row = tl_db.execute("SELECT * FROM tl_tokens WHERE provider='monzo'").fetchone()
        assert row is None

    def test_disconnect_noop_when_not_connected(self, tl_db: sqlite3.Connection):
        disconnect(tl_db, "monzo")  # must not raise

    def test_disconnect_leaves_other_providers(self, tl_db: sqlite3.Connection):
        for provider in ("monzo", "nationwide"):
            tl_db.execute(
                "INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
                (provider, "tok", "ref", _future()),
            )
        tl_db.commit()
        disconnect(tl_db, "monzo")
        remaining = tl_db.execute("SELECT provider FROM tl_tokens").fetchall()
        assert remaining == [("nationwide",)]
