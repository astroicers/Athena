# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for OAuthTokenManager."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def test_is_available_returns_false_when_no_file(tmp_path):
    """is_available() returns False when credentials file does not exist."""
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=tmp_path / "nonexistent.json")
    assert mgr.is_available() is False


def test_is_available_returns_false_when_file_empty(tmp_path):
    """is_available() returns False when file exists but has no accessToken."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"claudeAiOauth": {}}))
    from app.services.oauth_token_manager import OAuthTokenManager
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
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=creds_file)
    assert mgr.is_available() is True


@pytest.mark.asyncio
async def test_get_access_token_returns_cached_valid_token(tmp_path):
    """get_access_token() returns cached token if it has not expired."""
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=tmp_path / "credentials.json")
    mgr._access_token = "cached_token"
    mgr._expires_at = time.time() + 3600  # expires in 1 hour

    token = await mgr.get_access_token()
    assert token == "cached_token"


@pytest.mark.asyncio
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
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=creds_file)

    token = await mgr.get_access_token()
    assert token == "file_token"


@pytest.mark.asyncio
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
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=creds_file)

    with pytest.raises(ValueError, match="No refresh token"):
        await mgr.get_access_token()


@pytest.mark.asyncio
async def test_refresh_updates_access_token(tmp_path):
    """_refresh() calls the token endpoint and updates cached token."""
    from app.services.oauth_token_manager import OAuthTokenManager
    mgr = OAuthTokenManager(credentials_path=tmp_path / "credentials.json")
    mgr._refresh_token = "old_refresh"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 28800,
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.services.oauth_token_manager.httpx.AsyncClient", return_value=mock_client):
        await mgr._refresh()

    assert mgr._access_token == "new_access_token"
    assert mgr._refresh_token == "new_refresh_token"
    assert mgr._expires_at > time.time()
