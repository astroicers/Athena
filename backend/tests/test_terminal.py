"""Tests for terminal router helper functions (SPEC-024).

The main terminal endpoint is a WebSocket handler that requires a live
database, SSH/Metasploit connections, and a real WebSocket client — making
it an integration test that belongs in a separate suite.

This file covers the unit-testable pure functions extracted from
app/routers/terminal.py.
"""
import pytest

from app.routers.terminal import _is_dangerous, MAX_CMD_LEN


class TestIsDangerous:
    """Validate the command blacklist guard."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "RM -RF /",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            "> /dev/sda",
            "shred /dev/sda",
        ],
    )
    def test_dangerous_commands_are_blocked(self, cmd: str):
        assert _is_dangerous(cmd) is True

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "whoami",
            "cat /etc/passwd",
            "nmap -sV 10.0.0.1",
            "rm file.txt",
            "echo hello",
        ],
    )
    def test_safe_commands_are_allowed(self, cmd: str):
        assert _is_dangerous(cmd) is False


class TestMaxCmdLen:
    """Verify the constant is set to a reasonable value."""

    def test_max_cmd_len_is_1024(self):
        assert MAX_CMD_LEN == 1024
