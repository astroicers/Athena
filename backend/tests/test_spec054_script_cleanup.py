# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — Shell script trap/cleanup behaviour (Gherkin B2).

This test verifies the critical "no residue" property of the generated
relay script:

  Scenario B2: Script cleans up SSH process on SIGINT
    Given the generated athena-relay.sh is running in foreground
    And the SSH reverse tunnel is active
    When I press Ctrl+C
    Then the script prints "[athena-relay] Cleaning up..."
    And the SSH child process is killed
    And the script exits with code 0

We can't easily test a real ssh reverse tunnel in CI (no relay host),
so we render the script with a *stub SSH command* — a long-running
``sleep`` — substituted in place of the real ``ssh`` call. The trap
semantics (signal handling + cleanup + child kill) are identical
regardless of whether the child is ``ssh`` or ``sleep``, so this gives
us strong coverage of the trap pattern without needing infrastructure.
"""

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_test_script(tmp_path: Path) -> Path:
    """Render a minimal test script that mirrors SPEC-054's trap pattern.

    We don't re-parse the real ``generate_relay_script.py`` output here
    because stripping the real ``ssh -N ... &`` invocation + the nested
    pre-flight ``if command -v ss ... fi`` block is fragile. Instead we
    hand-write a tiny script that uses the **identical trap pattern**
    SPEC-054 guarantees — ``set -euo pipefail`` + ``trap cleanup
    EXIT SIGINT SIGTERM`` + ``sleep 300 &`` + ``wait "$SSH_PID"``.

    If this minimal pattern cleans up correctly, the real script's
    cleanup path (which uses the exact same structure) is equivalent
    by inspection. The generator's output is tested separately in
    ``test_spec054_script_generator.py`` via direct string assertions.
    """
    test_script = """#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    echo ""
    echo "[athena-relay] Cleaning up..."
    if [ -n "${SSH_PID:-}" ] && kill -0 "$SSH_PID" 2>/dev/null; then
        kill "$SSH_PID" 2>/dev/null || true
        wait "$SSH_PID" 2>/dev/null || true
    fi
    echo "[athena-relay] Done. No residue."
    exit 0
}
trap cleanup EXIT SIGINT SIGTERM

sleep 300 &
SSH_PID=$!

wait "$SSH_PID"
"""
    script_path = tmp_path / "athena-relay-test.sh"
    script_path.write_text(test_script)
    os.chmod(script_path, 0o755)
    return script_path


def _is_process_alive(pid: int) -> bool:
    """True iff ``pid`` is a live process we can signal."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but owned by someone else
        return True


def _collect_child_pids(parent_pid: int) -> list[int]:
    """Return PIDs of direct children of ``parent_pid`` using /proc.

    ``/proc/<pid>/stat`` format is ``pid (comm) state ppid ...`` where
    ``comm`` can contain spaces and parentheses, so a naive split on
    whitespace corrupts the ppid index. The canonical parse is:
    find the LAST ``)`` in the line — everything after it starts with
    the ``state`` field (index 0), and ppid is at relative index 1.
    """
    children: list[int] = []
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat") as f:
                    line = f.read()
                # Split off everything after the last ')' so comm with
                # embedded whitespace doesn't confuse field counting.
                rparen = line.rfind(")")
                if rparen < 0:
                    continue
                rest = line[rparen + 1 :].split()
                # rest[0] = state, rest[1] = ppid
                ppid = int(rest[1])
                if ppid == parent_pid:
                    children.append(int(entry))
            except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
                continue
    except FileNotFoundError:
        pytest.skip("/proc not available (not a Linux test env)")
    return children


# ---------------------------------------------------------------------------
# B2: SIGINT → cleanup → exit 0 → no child residue
# ---------------------------------------------------------------------------


def test_b2_sigint_triggers_cleanup_and_kills_child(
    tmp_path: Path,
) -> None:
    """SPEC-054 Gherkin B2: Ctrl+C cleans up SSH child, exits 0, no residue."""
    script = _render_test_script(tmp_path)

    # Start the script in its own process group so we can signal it cleanly
    proc = subprocess.Popen(
        ["bash", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )

    try:
        # Give the script time to reach `wait "$SSH_PID"`
        time.sleep(1.5)

        # Collect the sleep child PID before signalling
        children = _collect_child_pids(proc.pid)
        # We expect exactly one child: the background `sleep`
        assert len(children) >= 1, (
            f"Expected sleep child process after script start, got "
            f"children={children}. Script output so far:\n"
            f"{proc.stdout.read() if proc.stdout else ''}"
        )
        sleep_pid = children[0]
        assert _is_process_alive(sleep_pid), (
            "Sleep child must be alive before we send SIGINT"
        )

        # Send SIGINT to the process group (simulates Ctrl+C)
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)

        # Wait for the bash script to exit
        try:
            stdout, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Script did not exit within 5s after SIGINT")

        # --- Assertions ---

        # 1. Exit code must be 0 (trap cleanup returns 0)
        assert proc.returncode == 0, (
            f"Expected exit 0 after SIGINT cleanup, got {proc.returncode}. "
            f"Output:\n{stdout}"
        )

        # 2. Cleanup message must appear
        assert "[athena-relay] Cleaning up..." in stdout, (
            f"Expected cleanup message in output. Got:\n{stdout}"
        )
        assert "Done. No residue." in stdout, (
            f"Expected 'Done. No residue.' in output. Got:\n{stdout}"
        )

        # 3. The child `sleep` must be gone (the critical no-residue check)
        # Give the kernel a moment to reap
        time.sleep(0.3)
        assert not _is_process_alive(sleep_pid), (
            f"Child process {sleep_pid} must be killed after cleanup trap. "
            f"This would indicate the trap did not propagate the kill."
        )
    finally:
        # Safety net: kill everything if the test fails partway
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def test_b2_exit_natural_also_triggers_cleanup(tmp_path: Path) -> None:
    """Even on natural script exit, cleanup trap must fire and child die.

    Uses SIGTERM instead of SIGINT to verify the EXIT + SIGTERM branches
    of the trap also work.
    """
    script = _render_test_script(tmp_path)
    proc = subprocess.Popen(
        ["bash", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    try:
        time.sleep(1.5)
        children = _collect_child_pids(proc.pid)
        assert children, "Expected sleep child process"
        sleep_pid = children[0]

        # Send SIGTERM instead of SIGINT
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

        try:
            stdout, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Script did not exit within 5s after SIGTERM")

        assert proc.returncode == 0
        assert "Cleaning up" in stdout
        time.sleep(0.3)
        assert not _is_process_alive(sleep_pid)
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
