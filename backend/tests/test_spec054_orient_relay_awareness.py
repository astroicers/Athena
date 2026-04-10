# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — Orient prompt relay_available awareness.

Verifies SPEC-054 §Test Matrix P4 / N4 / B4 / S4 / S7:

  P4 (S4): settings.RELAY_IP set -> user prompt contains
           "relay_available: true" and "Relay LHOST: <ip>"
  N4 (S7): settings.RELAY_IP empty -> user prompt contains
           "relay_available: false"
  B4:      _ORIENT_SYSTEM_PROMPT contains the "Relay-aware exploit
           selection" paragraph and lists at least UnrealIRCd /
           Samba usermap_script / distccd as exploits to avoid when
           relay is unavailable

Rule #9 extension: when checked, Rule #9 must mention that the
reverse-shell pivot requires relay_available=true.
"""

import pytest

from app.services import orient_engine as orient_module


# ---------------------------------------------------------------------------
# B4 / Rule #9: Static system prompt contract
# ---------------------------------------------------------------------------


def test_b4_system_prompt_has_relay_aware_selection_section() -> None:
    """SPEC-054: Rule #8 must have a 'Relay-aware exploit selection' addendum."""
    prompt = orient_module._ORIENT_SYSTEM_PROMPT
    assert "Relay-aware exploit selection" in prompt, (
        "SPEC-054: Rule #8 must contain a 'Relay-aware exploit selection' "
        "paragraph that guides the LLM away from reverse-shell exploits "
        "when settings.RELAY_IP is unset."
    )


def test_system_prompt_names_reverse_shell_exploits_to_avoid() -> None:
    """The addendum must explicitly name UnrealIRCd, Samba, distccd."""
    prompt = orient_module._ORIENT_SYSTEM_PROMPT
    # These three are the reverse-shell class exploits we already support
    # via metasploit_client._EXPLOIT_MAP (plus distccd future)
    assert "UnrealIRCd" in prompt or "unreal_ircd" in prompt.lower()
    assert "Samba" in prompt or "samba" in prompt.lower()
    assert "distccd" in prompt.lower() or "distcc" in prompt.lower()


def test_system_prompt_allows_vsftpd_bind_shell_when_no_relay() -> None:
    """The addendum must explicitly allow vsftpd (bind shell) as fallback."""
    prompt = orient_module._ORIENT_SYSTEM_PROMPT
    # When relay is unavailable, bind shell exploits like vsftpd are still viable
    # Accept either literal "vsftpd" mention or "bind shell" phrasing
    has_vsftpd = "vsftpd" in prompt.lower()
    has_bind_shell = "bind shell" in prompt.lower()
    assert has_vsftpd or has_bind_shell, (
        "SPEC-054: the Relay-aware addendum must tell the LLM that bind "
        "shell exploits (e.g. vsftpd) remain viable without a relay."
    )


def test_rule_9_references_relay_available() -> None:
    """SPEC-054: Rule #9 must extend its trigger to require relay_available."""
    prompt = orient_module._ORIENT_SYSTEM_PROMPT
    # Rule #9 block should mention "relay_available" as an additional
    # condition before recommending reverse-shell T1190 subvariants
    assert "relay_available" in prompt.lower(), (
        "SPEC-054: Rule #9 (and/or Rule #8 addendum) must mention "
        "'relay_available' so the LLM knows when reverse-shell T1190 "
        "is actually viable."
    )


# ---------------------------------------------------------------------------
# User prompt template must have a placeholder for relay infrastructure
# ---------------------------------------------------------------------------


def test_user_prompt_template_has_relay_placeholder() -> None:
    """_ORIENT_USER_PROMPT_TEMPLATE must interpolate a relay_infrastructure block."""
    template = orient_module._ORIENT_USER_PROMPT_TEMPLATE
    assert "{relay_infrastructure}" in template, (
        "SPEC-054: _ORIENT_USER_PROMPT_TEMPLATE must contain a "
        "{relay_infrastructure} placeholder so _build_user_prompt can "
        "inject the Section 7.9 Infrastructure block."
    )


# ---------------------------------------------------------------------------
# _format_relay_infrastructure helper (pure, no DB)
# ---------------------------------------------------------------------------


def test_format_relay_infrastructure_when_relay_set() -> None:
    """When RELAY_IP is set, the helper outputs relay_available: true."""
    # The helper should be pure and testable without the full OrientEngine.
    # We expect it at module level so it can be imported here.
    assert hasattr(orient_module, "_format_relay_infrastructure"), (
        "SPEC-054: orient_engine.py must expose a module-level "
        "_format_relay_infrastructure() helper so it can be unit-tested "
        "without spinning up the whole OrientEngine."
    )
    from unittest.mock import patch

    with patch("app.services.orient_engine.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        result = orient_module._format_relay_infrastructure()

    assert "relay_available: true" in result.lower()
    assert "192.168.0.100" in result


def test_format_relay_infrastructure_when_relay_empty() -> None:
    """When RELAY_IP is empty, helper outputs relay_available: false."""
    from unittest.mock import patch

    with patch("app.services.orient_engine.settings") as mock_settings:
        mock_settings.RELAY_IP = ""
        result = orient_module._format_relay_infrastructure()

    assert "relay_available: false" in result.lower()
    # Must also make clear reverse-shell exploits are NOT viable
    lower = result.lower()
    assert "reverse shell" in lower or "reverse-shell" in lower
