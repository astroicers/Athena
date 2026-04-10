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

from app.config import Settings


def test_relay_ip_default_is_empty_string() -> None:
    """RELAY_IP default must be '' so empty == 'no relay' sentinel."""
    s = Settings()
    assert hasattr(s, "RELAY_IP")
    assert s.RELAY_IP == ""
    assert isinstance(s.RELAY_IP, str)


def test_relay_ssh_user_default() -> None:
    """RELAY_SSH_USER default must be 'athena-relay'."""
    s = Settings()
    assert hasattr(s, "RELAY_SSH_USER")
    assert s.RELAY_SSH_USER == "athena-relay"


def test_relay_ssh_port_default() -> None:
    """RELAY_SSH_PORT default must be 22 (int)."""
    s = Settings()
    assert hasattr(s, "RELAY_SSH_PORT")
    assert s.RELAY_SSH_PORT == 22
    assert isinstance(s.RELAY_SSH_PORT, int)


def test_relay_lport_default() -> None:
    """RELAY_LPORT default must be 4444 (int)."""
    s = Settings()
    assert hasattr(s, "RELAY_LPORT")
    assert s.RELAY_LPORT == 4444
    assert isinstance(s.RELAY_LPORT, int)


def test_relay_athena_host_default_is_empty_string() -> None:
    """RELAY_ATHENA_HOST default must be '' — must be set when RELAY_IP is set."""
    s = Settings()
    assert hasattr(s, "RELAY_ATHENA_HOST")
    assert s.RELAY_ATHENA_HOST == ""
    assert isinstance(s.RELAY_ATHENA_HOST, str)


def test_all_five_relay_settings_exist() -> None:
    """Sanity: all 5 RELAY_* settings are defined."""
    s = Settings()
    required = {
        "RELAY_IP",
        "RELAY_SSH_USER",
        "RELAY_SSH_PORT",
        "RELAY_LPORT",
        "RELAY_ATHENA_HOST",
    }
    for attr in required:
        assert hasattr(s, attr), f"Settings missing {attr}"
