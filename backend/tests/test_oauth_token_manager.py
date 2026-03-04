# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for OAuthTokenManager."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.oauth_token_manager import OAuthTokenManager


def test_is_available_returns_false_when_no_file(tmp_path):
    """is_available() returns False when credentials file does not exist."""
    mgr = OAuthTokenManager(credentials_path=tmp_path / "nonexistent.json")
    assert mgr.is_available() is False


def test_is_available_returns_false_when_file_empty(tmp_path):
    """is_available() returns False when file exists but has no accessToken."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"claudeAiOauth": {}}))
    mgr = OAuthTokenManager(credentials_path=creds_file)
    assert mgr.is_available() is False


def test_is_available_returns_false_when_file_malformed_json(tmp_path):
    """is_available() returns False when credentials file contains invalid JSON."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text("{not: valid json")
    mgr = OAuthTokenManager(credentials_path=creds_file)
    assert mgr.is_available() is False


def test_is_available_returns_true_when_valid_token(tmp_path):
    """is_available() returns True when credentials file has a valid accessToken."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "tok_test_123",
            "refreshToken": "ref_test_456",
            "expiresAt": int((time.time() + 3600) * 1000),
        }
    }))
    mgr = OAuthTokenManager(credentials_path=creds_file)
    assert mgr.is_available() is True


async def test_get_access_token_returns_cached_valid_token(tmp_path):
    """get_access_token() returns cached token if it has not expired."""
    mgr = OAuthTokenManager(credentials_path=tmp_path / "credentials.json")
    mgr._access_token = "cached_token"
    mgr._expires_at = time.time() + 3600  # expires in 1 hour

    token = await mgr.get_access_token()
    assert token == "cached_token"


async def test_get_access_token_refreshes_within_5min_buffer(tmp_path):
    """get_access_token() does NOT return cached token when within 5-minute buffer."""
    future_expiry = int((time.time() + 3600) * 1000)
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "file_token_fresh",
            "refreshToken": "ref_token",
            "expiresAt": future_expiry,
        }
    }))
    mgr = OAuthTokenManager(credentials_path=creds_file)
    # Set cached token to expire in 60 seconds (within 5-min buffer)
    mgr._access_token = "about_to_expire"
    mgr._expires_at = time.time() + 60  # < 300 second buffer

    # Should NOT return the cached "about_to_expire" token,
    # should instead load the fresh token from file
    token = await mgr.get_access_token()
    assert token == "file_token_fresh"
    assert token != "about_to_expire"


async def test_get_access_token_loads_from_file_when_cache_empty(tmp_path):
    """get_access_token() reads token from file when cache is empty."""
    future_expiry = int((time.time() + 3600) * 1000)
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "file_token",
            "refreshToken": "ref_token",
            "expiresAt": future_expiry,
        }
    }))
    mgr = OAuthTokenManager(credentials_path=creds_file)

    token = await mgr.get_access_token()
    assert token == "file_token"


async def test_get_access_token_raises_when_no_refresh_token(tmp_path):
    """get_access_token() raises ValueError when token is expired and no refresh token."""
    past_expiry = int((time.time() - 3600) * 1000)  # expired 1 hour ago
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "expired_token",
            "expiresAt": past_expiry,
        }
    }))
    mgr = OAuthTokenManager(credentials_path=creds_file)

    with pytest.raises(ValueError, match="No refresh token available"):
        await mgr.get_access_token()


async def test_refresh_updates_access_token(tmp_path):
    """_refresh() calls the token endpoint and updates cached token."""
    mgr = OAuthTokenManager(credentials_path=tmp_path / "credentials.json")
    mgr._refresh_token = "old_refresh"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 28800,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.oauth_token_manager.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        await mgr._refresh()

    assert mgr._access_token == "new_access_token"
    assert mgr._refresh_token == "new_refresh_token"
    assert mgr._expires_at > time.time()
