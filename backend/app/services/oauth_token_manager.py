# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Manage Claude Code OAuth credentials (~/.claude/.credentials.json).

Reads the OAuth token written by `claude login`, auto-refreshes when expired,
and provides the access token + required beta header for API calls.
"""

import json
import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"
_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_SCOPES = "user:profile user:inference user:sessions:claude_code user:mcp_servers"
OAUTH_BETA_HEADER = "oauth-2025-04-20"


class OAuthTokenManager:
    """Read and auto-refresh OAuth tokens from Claude Code credentials."""

    def __init__(self, credentials_path: Path | None = None):
        self._credentials_path = credentials_path or _CREDENTIALS_PATH
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0  # epoch seconds

    def is_available(self) -> bool:
        """Check if credentials file exists with a valid token."""
        return self._credentials_path.exists() and self._load_from_file() is not None

    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        # Return cached token if still valid (with 5-min buffer)
        if self._access_token and time.time() < (self._expires_at - 300):
            return self._access_token

        # Try load from file (Claude Code may have refreshed it externally)
        creds = self._load_from_file()
        if creds and creds["expires_at"] / 1000 > time.time() + 300:
            self._access_token = creds["access_token"]
            self._refresh_token = creds["refresh_token"]
            self._expires_at = creds["expires_at"] / 1000
            return self._access_token

        # Need to refresh — get refresh token from memory or file
        if not self._refresh_token and creds:
            self._refresh_token = creds["refresh_token"]
        if not self._refresh_token:
            raise ValueError("No refresh token available for Claude OAuth")

        await self._refresh()
        return self._access_token

    def _load_from_file(self) -> dict | None:
        """Load credentials from the Claude Code credentials file."""
        try:
            data = json.loads(self._credentials_path.read_text())
            oauth = data.get("claudeAiOauth", {})
            if oauth.get("accessToken"):
                return {
                    "access_token": oauth["accessToken"],
                    "refresh_token": oauth.get("refreshToken"),
                    "expires_at": oauth.get("expiresAt", 0),
                }
        except Exception:
            logger.debug("Failed to load OAuth credentials from %s", self._credentials_path)
        return None

    async def _refresh(self):
        """Refresh the OAuth token via platform.claude.com."""
        logger.info("Refreshing Claude OAuth token...")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": _CLIENT_ID,
                    "scope": _SCOPES,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + data.get("expires_in", 28800)
        logger.info("OAuth token refreshed, expires in %ds", data.get("expires_in"))
