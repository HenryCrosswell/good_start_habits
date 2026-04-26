"""TrueLayer OAuth client and Data API wrapper.

Each public function takes an open sqlite3.Connection and returns either a
plain value or raises no exceptions — failures are logged and return empty/None
so the budget page degrades gracefully.
"""

import base64
import hashlib
import logging
import os
import secrets
import sqlite3
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

log = logging.getLogger(__name__)

_SCOPES = "info accounts transactions balance offline_access"


def _is_sandbox() -> bool:
    return os.getenv("TRUELAYER_SANDBOX", "false").lower() == "true"


def _auth_base() -> str:
    return (
        "https://auth.truelayer-sandbox.com"
        if _is_sandbox()
        else "https://auth.truelayer.com"
    )


def _api_base() -> str:
    return (
        "https://api.truelayer-sandbox.com/data/v1"
        if _is_sandbox()
        else "https://api.truelayer.com/data/v1"
    )


_STATE_TTL = timedelta(minutes=10)
_REFRESH_BUFFER = timedelta(minutes=5)

# Providers the budget page offers. Values are TrueLayer provider IDs
# used in production to pre-select the bank in the auth UI.
PROVIDERS = ["monzo", "nationwide", "amex"]
_PROVIDER_IDS = {
    "monzo": "uk-ob-monzo",
    "nationwide": "uk-ob-nationwide",
    "amex": "uk-oauth-amex",
}

# TrueLayer exposes credit cards under /cards, not /accounts.
_CARD_PROVIDERS = {"amex"}


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256 method."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------


def start_auth(con: sqlite3.Connection, provider_hint: str) -> str:
    """Generate PKCE pair + CSRF state, persist both, return the auth URL.

    The state and code_verifier are stored in ``oauth_state`` and consumed
    exactly once in :func:`finish_auth`.
    """
    verifier, challenge = _make_pkce_pair()
    state = _b64url(secrets.token_bytes(32))
    expires_at = (datetime.now(timezone.utc) + _STATE_TTL).isoformat()

    # Purge stale states before inserting
    con.execute(
        "DELETE FROM oauth_state WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    con.execute(
        "INSERT INTO oauth_state (state, provider_hint, code_verifier, expires_at)"
        " VALUES (?, ?, ?, ?)",
        (state, provider_hint, verifier, expires_at),
    )
    con.commit()

    params: dict[str, str] = {
        "response_type": "code",
        "client_id": os.environ["TRUELAYER_CLIENT_ID"],
        "scope": _SCOPES,
        "redirect_uri": os.environ["TRUELAYER_REDIRECT_URI"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if _is_sandbox():
        params["providers"] = "mock"
    else:
        provider_id = _PROVIDER_IDS.get(provider_hint)
        if provider_id:
            params["providers"] = provider_id

    return f"{_auth_base()}/?{urllib.parse.urlencode(params)}"


def finish_auth(
    con: sqlite3.Connection, code: str, state: str
) -> tuple[str | None, dict[str, Any] | None]:
    """Verify CSRF state, exchange code for tokens.

    Returns ``(provider_hint, token_data)`` on success, ``(None, None)``
    on any failure. The state row is always deleted (single-use).
    """
    row = con.execute(
        "SELECT provider_hint, code_verifier, expires_at"
        " FROM oauth_state WHERE state = ?",
        (state,),
    ).fetchone()

    # Delete regardless — state must never be reused
    con.execute("DELETE FROM oauth_state WHERE state = ?", (state,))
    con.commit()

    if not row:
        log.warning("OAuth callback received unknown state")
        return None, None

    provider_hint, code_verifier, expires_at_str = row

    if datetime.fromisoformat(expires_at_str) < datetime.now(timezone.utc):
        log.warning("OAuth state expired for provider %s", provider_hint)
        return None, None

    try:
        resp = requests.post(
            f"{_auth_base()}/connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": os.environ["TRUELAYER_CLIENT_ID"],
                "client_secret": os.environ["TRUELAYER_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": os.environ["TRUELAYER_REDIRECT_URI"],
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return provider_hint, resp.json()
    except requests.RequestException as exc:
        log.error("Token exchange failed for %s: %s", provider_hint, exc)
        return None, None


# ---------------------------------------------------------------------------
# Token storage and refresh
# ---------------------------------------------------------------------------


def save_tokens(
    con: sqlite3.Connection, provider: str, token_data: dict[str, Any]
) -> None:
    """Persist access + refresh tokens for a provider."""
    expires_in = int(token_data.get("expires_in", 3600))
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    con.execute(
        """
        INSERT INTO tl_tokens (provider, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            access_token  = excluded.access_token,
            refresh_token = COALESCE(excluded.refresh_token, refresh_token),
            expires_at    = excluded.expires_at,
            created_at    = datetime('now')
        """,
        (
            provider,
            token_data["access_token"],
            token_data.get("refresh_token"),
            expires_at,
        ),
    )
    con.commit()


def _do_refresh(refresh_tok: str) -> dict[str, Any]:
    resp = requests.post(
        f"{_auth_base()}/connect/token",
        data={
            "grant_type": "refresh_token",
            "client_id": os.environ["TRUELAYER_CLIENT_ID"],
            "client_secret": os.environ["TRUELAYER_CLIENT_SECRET"],
            "refresh_token": refresh_tok,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_valid_token(con: sqlite3.Connection, provider: str) -> str | None:
    """Return a valid access token, silently refreshing if near expiry."""
    row = con.execute(
        "SELECT access_token, refresh_token, expires_at"
        " FROM tl_tokens WHERE provider = ?",
        (provider,),
    ).fetchone()
    if not row:
        return None

    access_token, refresh_tok, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str)

    if datetime.now(timezone.utc) < expires_at - _REFRESH_BUFFER:
        return access_token

    if not refresh_tok:
        log.warning("Token for %s is expired and no refresh token is stored", provider)
        return None

    try:
        token_data = _do_refresh(refresh_tok)
        save_tokens(con, provider, token_data)
        return token_data["access_token"]
    except requests.RequestException as exc:
        log.error("Token refresh failed for %s: %s", provider, exc)
        return None


# ---------------------------------------------------------------------------
# Data API
# ---------------------------------------------------------------------------


def get_transactions(
    con: sqlite3.Connection,
    provider: str,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return transactions for a connected provider back to ``since``.

    Defaults to the last 30 days when ``since`` is not given.
    Returns an empty list if the provider is not connected or any API call
    fails — never raises.
    """
    token = get_valid_token(con, provider)
    if not token:
        return []

    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"Authorization": f"Bearer {token}"}

    resource = "cards" if provider in _CARD_PROVIDERS else "accounts"

    try:
        list_resp = requests.get(
            f"{_api_base()}/{resource}",
            headers=headers,
            timeout=15,
        )
        list_resp.raise_for_status()
        accounts = list_resp.json().get("results", [])
    except requests.RequestException as exc:
        log.error("Failed to fetch %s for %s: %s", resource, provider, exc)
        return []

    transactions: list[dict[str, Any]] = []
    for account in accounts:
        account_id = account.get("account_id", "")
        try:
            txn_resp = requests.get(
                f"{_api_base()}/{resource}/{account_id}/transactions",
                params={"from": since_str},
                headers=headers,
                timeout=15,
            )
            txn_resp.raise_for_status()
            for txn in txn_resp.json().get("results", []):
                txn["_provider"] = provider
                transactions.append(txn)
        except requests.RequestException as exc:
            log.warning(
                "Failed to fetch transactions for %s / %s %s: %s",
                provider,
                resource[:-1],
                account_id,
                exc,
            )

    return transactions


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def get_connection_status(con: sqlite3.Connection) -> dict[str, str]:
    """Return 'connected' or 'disconnected' for each provider."""
    rows = con.execute("SELECT provider FROM tl_tokens").fetchall()
    connected = {row[0] for row in rows}
    return {p: ("connected" if p in connected else "disconnected") for p in PROVIDERS}


def disconnect(con: sqlite3.Connection, provider: str) -> None:
    """Remove stored tokens for a provider."""
    con.execute("DELETE FROM tl_tokens WHERE provider = ?", (provider,))
    con.commit()


# ---------------------------------------------------------------------------
# APScheduler backstop
# ---------------------------------------------------------------------------


def refresh_all(con: sqlite3.Connection) -> None:
    """Proactively refresh all tokens nearing expiry.

    Called by a background APScheduler job — the primary refresh path is
    per-request via :func:`get_valid_token`.
    """
    rows = con.execute(
        "SELECT provider, refresh_token, expires_at FROM tl_tokens"
    ).fetchall()
    for provider, refresh_tok, expires_at_str in rows:
        if not refresh_tok:
            continue
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(timezone.utc) >= expires_at - timedelta(minutes=15):
            try:
                token_data = _do_refresh(refresh_tok)
                save_tokens(con, provider, token_data)
                log.info("Proactively refreshed token for %s", provider)
            except requests.RequestException as exc:
                log.error("Scheduled refresh failed for %s: %s", provider, exc)
