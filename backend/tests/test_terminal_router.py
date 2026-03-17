# Copyright (c) 2025 Athena Red Team Platform
# Author: azz093093.830330@gmail.com
# Project: Athena
# License: MIT
#
# This file is part of the Athena Red Team Platform.
# Unauthorized copying or distribution is prohibited.

"""Unit tests for terminal router _is_dangerous() guard function.

The WebSocket endpoint uses db_manager.connection() directly (not DI get_db),
so full integration tests via the test client are not feasible.  These tests
focus exclusively on the pure-Python _is_dangerous() helper.
"""

import pytest

from app.routers.terminal import _is_dangerous


# ---------------------------------------------------------------------------
# Blocked commands — every entry in _CMD_BLACKLIST must be rejected
# ---------------------------------------------------------------------------

class TestBlockedCommands:
    def test_blocks_rm_rf_root(self):
        assert _is_dangerous("rm -rf /") is True

    def test_blocks_rm_rf_with_trailing_content(self):
        # substring match — "rm -rf /" anywhere in the command is blocked
        assert _is_dangerous("sudo rm -rf / --no-preserve-root") is True

    def test_blocks_mkfs(self):
        assert _is_dangerous("mkfs /dev/sda") is True

    def test_blocks_mkfs_variant(self):
        assert _is_dangerous("mkfs.ext4 /dev/sdb1") is True

    def test_blocks_dd_zero(self):
        assert _is_dangerous("dd if=/dev/zero of=/dev/sda") is True

    def test_blocks_dd_zero_with_options(self):
        assert _is_dangerous("dd if=/dev/zero of=/dev/sda bs=512 count=1") is True

    def test_blocks_redirect_dev_sda(self):
        assert _is_dangerous("> /dev/sda") is True

    def test_blocks_redirect_dev_sda_inline(self):
        assert _is_dangerous("cat /dev/urandom > /dev/sda") is True

    def test_blocks_shred_dev(self):
        assert _is_dangerous("shred /dev/sda") is True

    def test_blocks_shred_dev_variant(self):
        assert _is_dangerous("shred /dev/nvme0n1") is True


# ---------------------------------------------------------------------------
# Case-insensitivity — blacklist match is lower-cased
# ---------------------------------------------------------------------------

class TestCaseInsensitivity:
    def test_blocks_rm_rf_uppercase(self):
        assert _is_dangerous("RM -RF /") is True

    def test_blocks_mkfs_mixed_case(self):
        assert _is_dangerous("MkFs /dev/sda") is True

    def test_blocks_shred_dev_uppercase(self):
        assert _is_dangerous("SHRED /DEV/sda") is True


# ---------------------------------------------------------------------------
# Allowed commands — normal operations must not be blocked
# ---------------------------------------------------------------------------

class TestAllowedCommands:
    def test_allows_whoami(self):
        assert _is_dangerous("whoami") is False

    def test_allows_ls(self):
        assert _is_dangerous("ls -la /tmp") is False

    def test_allows_id(self):
        assert _is_dangerous("id") is False

    def test_allows_uname(self):
        assert _is_dangerous("uname -a") is False

    def test_allows_cat_passwd(self):
        assert _is_dangerous("cat /etc/passwd") is False

    def test_allows_ps(self):
        assert _is_dangerous("ps aux") is False

    def test_allows_ifconfig(self):
        assert _is_dangerous("ifconfig") is False

    def test_allows_empty_string(self):
        assert _is_dangerous("") is False

    def test_allows_plain_rm(self):
        # "rm -rf /" requires the exact substring; a safe rm should pass
        assert _is_dangerous("rm somefile.txt") is False

    def test_allows_redirect_to_tmp(self):
        # "> /dev/sda" is blocked but redirecting elsewhere is fine
        assert _is_dangerous("echo hello > /tmp/out.txt") is False

    def test_allows_dd_without_zero_src(self):
        # only "dd if=/dev/zero" is blocked; dd of other sources is allowed
        assert _is_dangerous("dd if=/dev/sda of=/tmp/backup.img") is False
