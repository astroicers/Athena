# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — RELAY_* settings defaults and types.

Verifies the 5 new settings fields exist on ``Settings`` with the
documented defaults and types. These are the contract the rest of
SPEC-054 relies on.
"""

import pytest

from app.config import Settings


_RELAY_ENV_VARS = (
    "RELAY_IP", "RELAY_SSH_USER", "RELAY_SSH_PORT",
    "RELAY_LPORT", "RELAY_ATHENA_HOST",
)


@pytest.fixture(autouse=True)
def _clean_relay_env(monkeypatch):
    """Remove RELAY_* env vars so Settings reads pure defaults."""
    for var in _RELAY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _defaults() -> Settings:
    """Create Settings without .env file influence."""
    return Settings(_env_file=None)


def test_relay_ip_default_is_empty_string() -> None:
    s = _defaults()
    assert hasattr(s, "RELAY_IP")
    assert s.RELAY_IP == ""
    assert isinstance(s.RELAY_IP, str)


def test_relay_ssh_user_default() -> None:
    s = _defaults()
    assert hasattr(s, "RELAY_SSH_USER")
    assert s.RELAY_SSH_USER == "athena-relay"


def test_relay_ssh_port_default() -> None:
    s = _defaults()
    assert hasattr(s, "RELAY_SSH_PORT")
    assert s.RELAY_SSH_PORT == 22
    assert isinstance(s.RELAY_SSH_PORT, int)


def test_relay_lport_default() -> None:
    s = _defaults()
    assert hasattr(s, "RELAY_LPORT")
    assert s.RELAY_LPORT == 4444
    assert isinstance(s.RELAY_LPORT, int)


def test_relay_athena_host_default_is_empty_string() -> None:
    s = _defaults()
    assert hasattr(s, "RELAY_ATHENA_HOST")
    assert s.RELAY_ATHENA_HOST == ""
    assert isinstance(s.RELAY_ATHENA_HOST, str)


def test_all_five_relay_settings_exist() -> None:
    s = _defaults()
    for attr in _RELAY_ENV_VARS:
        assert hasattr(s, attr), f"Settings missing {attr}"
