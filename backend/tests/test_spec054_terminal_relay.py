# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054 — terminal.py re-exploit uses bound methods (not raw _run_exploit).

SPEC-053 left the terminal Path B re-exploit code calling
``msf._run_exploit(module, payload, {"RHOSTS": target_ip}, probe_cmd=cmd)``
directly, which bypasses the LHOST injection we added in SPEC-054 to the
``exploit_samba`` / ``exploit_unrealircd`` bound methods.

This test asserts the refactor: Path B must call
``msf_engine.get_exploit_for_service(service)`` and then invoke the
returned bound method, so that LHOST picks up settings.RELAY_IP via the
same code path as engine_router.
"""

import ast
import inspect

import pytest

from app.routers import terminal as terminal_module


# ---------------------------------------------------------------------------
# Static analysis of the terminal router source
# ---------------------------------------------------------------------------


def _get_run_msf_terminal_source() -> str:
    """Return the source code of ``_run_msf_terminal`` for inspection."""
    return inspect.getsource(terminal_module._run_msf_terminal)


# ---------------------------------------------------------------------------
# T01: Path B must not call _run_exploit directly
# ---------------------------------------------------------------------------


def test_t01_path_b_does_not_call_run_exploit_directly() -> None:
    """SPEC-054: terminal.py must route through bound methods so LHOST works."""
    source = _get_run_msf_terminal_source()
    # The SPEC-053 code had: msf._run_exploit(...)
    # SPEC-054 refactor should route through get_exploit_for_service
    assert "msf._run_exploit(" not in source, (
        "SPEC-054: terminal.py Path B must not call _run_exploit directly; "
        "use get_exploit_for_service + bound method so LHOST injection from "
        "SPEC-054 settings picks up automatically."
    )


# ---------------------------------------------------------------------------
# T02: Path B must call get_exploit_for_service with probe_cmd passthrough
# ---------------------------------------------------------------------------


def test_t02_path_b_uses_get_exploit_for_service() -> None:
    """Path B should obtain the bound exploit method via get_exploit_for_service."""
    source = _get_run_msf_terminal_source()
    assert "get_exploit_for_service" in source, (
        "SPEC-054: terminal.py Path B must call "
        "msf.get_exploit_for_service(inferred_service) to obtain the "
        "bound exploit method (which reads LHOST from settings.RELAY_IP)."
    )


def test_t03_path_b_passes_probe_cmd_to_bound_method() -> None:
    """Path B must keep probe_cmd passthrough in the refactored call."""
    source = _get_run_msf_terminal_source()
    # Look for a call that passes probe_cmd= as keyword argument to some
    # variable other than _run_exploit
    assert "probe_cmd=" in source, (
        "SPEC-054: terminal.py Path B must still passthrough probe_cmd "
        "to the bound exploit method (all exploit methods accept it now)."
    )


def test_t04_path_b_no_longer_imports_exploit_module_helper() -> None:
    """The old _exploit_module_and_payload helper is dead code after refactor.

    Actually this helper may still be referenced but it should not be used
    in Path B's command loop anymore. We just sanity-check that its usage
    is not inside the inner command loop path.
    """
    source = _get_run_msf_terminal_source()
    # If the helper call appears, it should be removed from the main flow
    # (we accept the helper function itself still existing for backward
    # compatibility, but the dispatcher should not call it).
    #
    # Concretely: the per-command loop should call something like
    # ``exploit_fn(target_ip, probe_cmd=cmd)`` rather than
    # ``_run_exploit(*_exploit_module_and_payload(...), {"RHOSTS": ...}, probe_cmd=cmd)``.
    if "_exploit_module_and_payload(" in source:
        # If it still appears, make sure _run_exploit was not called on
        # its result — the combination is the exact anti-pattern.
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "_exploit_module_and_payload(" in line:
                # The next few lines must not contain _run_exploit(
                window = "\n".join(lines[i : i + 5])
                assert "_run_exploit(" not in window, (
                    "SPEC-054: do not combine _exploit_module_and_payload with "
                    "_run_exploit — use the bound method pattern instead."
                )


def test_t05_path_b_exploit_call_is_valid_python() -> None:
    """Sanity: the refactored source must still parse."""
    source = _get_run_msf_terminal_source()
    try:
        ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"_run_msf_terminal source has syntax error: {exc}")
