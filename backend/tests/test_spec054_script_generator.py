# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — CLI generate_relay_script output + exit code contract.

Verifies SPEC-054 §Test Matrix P3 / N1 / N2 / B1:

  P3: valid settings -> full bash script to stdout, exit 0
  N1: RELAY_IP empty -> stderr mentions "RELAY_IP not set", exit 1
  N2: RELAY_IP set but RELAY_ATHENA_HOST empty -> stderr mentions
      "RELAY_ATHENA_HOST not set", exit 1
  B1: default RELAY_LPORT=4444 rendered into script

The CLI module is imported and its ``main()`` is called directly so we
can capture stdout/stderr without subprocess overhead. Settings are
patched per-test.
"""

import io
import sys
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(monkeypatch: pytest.MonkeyPatch) -> tuple[int, str, str]:
    """Invoke generate_relay_script.main() and capture (exit, stdout, stderr)."""
    from app.cli import generate_relay_script  # noqa: PLC0415

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout_buf)
    monkeypatch.setattr(sys, "stderr", stderr_buf)
    exit_code = generate_relay_script.main()
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


# ---------------------------------------------------------------------------
# P3: Valid settings -> full script on stdout
# ---------------------------------------------------------------------------


def test_p3_generate_script_with_valid_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-054 S3: all settings valid -> complete bash script + exit 0."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.RELAY_ATHENA_HOST = "192.168.96.83"
        mock_settings.RELAY_SSH_USER = "athena-relay"
        mock_settings.RELAY_SSH_PORT = 22
        mock_settings.RELAY_LPORT = 4444

        exit_code, stdout, stderr = _run_cli(monkeypatch)

    assert exit_code == 0, f"exit={exit_code} stderr={stderr}"

    # Shebang
    assert stdout.startswith("#!/usr/bin/env bash")
    # Core contract assertions from SPEC-054 Gherkin S3
    assert 'RELAY_IP="192.168.0.100"' in stdout
    assert 'ATHENA_HOST="192.168.96.83"' in stdout
    assert 'SSH_USER="athena-relay"' in stdout
    assert "LPORT=4444" in stdout
    # Safety posture
    assert "set -euo pipefail" in stdout
    assert "trap cleanup EXIT SIGINT SIGTERM" in stdout
    # Tunnel command
    assert "ssh -N" in stdout
    assert "ExitOnForwardFailure=yes" in stdout
    assert 'ServerAliveInterval=30' in stdout
    # Reverse tunnel spec — the LPORT variable is referenced in the bash
    # string (variable syntax), so assert on a stable substring
    assert '-R "0.0.0.0:${LPORT}:${ATHENA_HOST}:${LPORT}"' in stdout


# ---------------------------------------------------------------------------
# N1: RELAY_IP missing -> exit 1 + stderr
# ---------------------------------------------------------------------------


def test_n1_generate_script_fails_when_relay_ip_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-054 S5: RELAY_IP='' -> stderr mentions it, exit 1."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = ""
        mock_settings.RELAY_ATHENA_HOST = ""
        mock_settings.RELAY_SSH_USER = "athena-relay"
        mock_settings.RELAY_SSH_PORT = 22
        mock_settings.RELAY_LPORT = 4444

        exit_code, stdout, stderr = _run_cli(monkeypatch)

    assert exit_code == 1
    assert "RELAY_IP" in stderr
    assert "not set" in stderr.lower()
    # Must not emit a script to stdout on error
    assert stdout == ""


# ---------------------------------------------------------------------------
# N2: RELAY_ATHENA_HOST missing -> exit 1 + stderr
# ---------------------------------------------------------------------------


def test_n2_generate_script_fails_when_athena_host_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-054 S5b: RELAY_IP set but RELAY_ATHENA_HOST='' -> exit 1."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.RELAY_ATHENA_HOST = ""
        mock_settings.RELAY_SSH_USER = "athena-relay"
        mock_settings.RELAY_SSH_PORT = 22
        mock_settings.RELAY_LPORT = 4444

        exit_code, stdout, stderr = _run_cli(monkeypatch)

    assert exit_code == 1
    assert "RELAY_ATHENA_HOST" in stderr
    assert stdout == ""


# ---------------------------------------------------------------------------
# B1: Default RELAY_LPORT rendered correctly
# ---------------------------------------------------------------------------


def test_b1_default_lport_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC-054 B1: default RELAY_LPORT=4444 end-to-end in script output."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.RELAY_ATHENA_HOST = "192.168.96.83"
        mock_settings.RELAY_SSH_USER = "athena-relay"
        mock_settings.RELAY_SSH_PORT = 22
        mock_settings.RELAY_LPORT = 4444  # default

        exit_code, stdout, _ = _run_cli(monkeypatch)

    assert exit_code == 0
    assert "LPORT=4444" in stdout


def test_custom_lport_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom LPORT (e.g. 5555) must be respected — no hardcoded 4444."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.RELAY_ATHENA_HOST = "192.168.96.83"
        mock_settings.RELAY_SSH_USER = "athena-relay"
        mock_settings.RELAY_SSH_PORT = 22
        mock_settings.RELAY_LPORT = 5555

        exit_code, stdout, _ = _run_cli(monkeypatch)

    assert exit_code == 0
    assert "LPORT=5555" in stdout
    # Ensure no stray 4444 literal
    assert "LPORT=4444" not in stdout


def test_custom_ssh_port_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom SSH_PORT must appear in the script."""
    with patch("app.cli.generate_relay_script.settings") as mock_settings:
        mock_settings.RELAY_IP = "192.168.0.100"
        mock_settings.RELAY_ATHENA_HOST = "192.168.96.83"
        mock_settings.RELAY_SSH_USER = "pentester"
        mock_settings.RELAY_SSH_PORT = 2222
        mock_settings.RELAY_LPORT = 4444

        exit_code, stdout, _ = _run_cli(monkeypatch)

    assert exit_code == 0
    assert 'SSH_PORT="2222"' in stdout
    assert 'SSH_USER="pentester"' in stdout
