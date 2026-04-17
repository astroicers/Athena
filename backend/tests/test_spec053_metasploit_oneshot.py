# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-053 Test Matrix — metasploit_client one-shot exploit mode.

Covers test cases T03 and T04 from SPEC-053 §Test Matrix. T07 (terminal
re-exploit) is deferred because it requires a live websocket fixture
which exceeds the scope of a unit test; it will be exercised by the
end-to-end demo verification step.

    T03: _run_exploit in one-shot mode releases the session after probe
    T04: _run_exploit returns failure_category-friendly error on connect
         failure (handled via _classify_failure in engine_router)

Because the real MetasploitRPCEngine needs a running msfrpcd, we patch
``_connect`` and stub the session list to drive the state machine.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.metasploit_client import MetasploitRPCEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubSession:
    """Minimal stand-in for a pymetasploit3 session."""

    def __init__(self, sid: str):
        self._sid = sid
        self.writes: list[str] = []
        # Provide enough reads for the one-shot flow:
        # 1. drain banner, 2. drain echo sentinel, 3. probe output
        self._reads: list[str] = [
            "Welcome to shell\n",
            "ATHENA_PROBE_START\n",
            "uid=0(root) gid=0(root)\nLinux metasploitable\nmetasploitable\n",
        ]
        self.stopped = False

    def write(self, data: str) -> None:
        self.writes.append(data)

    def read(self) -> str:
        if self._reads:
            return self._reads.pop(0)
        return ""

    def stop(self) -> None:
        self.stopped = True


class _StubSessionsList(dict):
    """Dict-like stub for client.sessions.list with mutable state.

    The real msfrpc client returns a fresh dict on each access; we
    emulate that by storing state on self and letting the caller
    mutate ``_opened`` to indicate a new session has been spawned.
    """

    def __init__(self):
        super().__init__()
        self._opened: dict[str, dict] = {}

    def __iter__(self):
        return iter(self._opened)

    def __getitem__(self, key):
        return self._opened[key]

    def __contains__(self, key):
        return key in self._opened

    def items(self):
        return self._opened.items()

    def keys(self):
        return self._opened.keys()

    def values(self):
        return self._opened.values()


class _StubClient:
    """Stub MsfRpcClient. The test controls when a new session appears."""

    def __init__(self):
        self.sessions = MagicMock()
        self._sessions_store: dict[str, dict] = {}
        self.sessions.list = self._sessions_store  # mutable dict
        self.sessions.session = lambda sid: self._session_objs[sid]
        self._session_objs: dict[str, _StubSession] = {}
        self.modules = MagicMock()
        self.modules.use = MagicMock(return_value=MagicMock(execute=MagicMock()))

    def open_session(self, sid: str) -> _StubSession:
        sess = _StubSession(sid)
        self._sessions_store[sid] = {"target_host": "192.168.0.26", "type": "shell"}
        self._session_objs[sid] = sess
        return sess


# ---------------------------------------------------------------------------
# T03: One-shot mode releases session after probe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t03_run_exploit_releases_session_after_probe() -> None:
    """One-shot: launch exploit -> probe -> shell.stop() -> return.

    After _run_exploit returns success, the session must have been
    stopped (``shell.stopped == True``). The SPEC-053 invariant: no
    persistent shell.
    """
    from app.config import settings

    client = _StubClient()

    # When exploit.execute() is called, immediately "open" a new session.
    opened_sess: list[_StubSession] = []

    def _exec_side_effect(*args, **kwargs):
        s = client.open_session("session_42")
        opened_sess.append(s)
        return MagicMock()

    client.modules.use.return_value.execute = MagicMock(side_effect=_exec_side_effect)

    engine = MetasploitRPCEngine()

    # Patch _connect to return our stub client
    with patch.object(engine, "_connect", return_value=client), \
         patch("app.clients.metasploit_client.asyncio.sleep", new_callable=AsyncMock), \
         patch.object(settings, "MOCK_METASPLOIT", False), \
         patch.object(settings, "METASPLOIT_SESSION_WAIT_SEC", 2):
        result = await engine._run_exploit(
            "exploit/unix/ftp/vsftpd_234_backdoor",
            "cmd/unix/interact",
            {"RHOSTS": "192.168.0.26"},
        )

    assert result["status"] == "success", result
    assert result["shell"] == "session_42"
    assert "uid=0(root)" in result["output"]

    # The SPEC-053 invariant: session was stopped after probe
    assert len(opened_sess) == 1
    assert opened_sess[0].stopped is True, (
        "one-shot mode must call shell.stop() to release the session"
    )
    # Probe command was the default
    assert any("id; uname -a; hostname" in w for w in opened_sess[0].writes)


@pytest.mark.asyncio
async def test_t03_custom_probe_cmd_is_used() -> None:
    """The probe_cmd parameter is honored and written to the shell."""
    from app.config import settings

    client = _StubClient()

    def _exec_side_effect(*args, **kwargs):
        client.open_session("session_99")
        return MagicMock()

    client.modules.use.return_value.execute = MagicMock(side_effect=_exec_side_effect)

    engine = MetasploitRPCEngine()

    with patch.object(engine, "_connect", return_value=client), \
         patch.object(engine, "_read_shell_output", new=AsyncMock(return_value="ok")), \
         patch.object(settings, "MOCK_METASPLOIT", False):
        result = await engine._run_exploit(
            "exploit/unix/ftp/vsftpd_234_backdoor",
            "cmd/unix/interact",
            {"RHOSTS": "192.168.0.26"},
            probe_cmd="whoami",
        )

    assert result["status"] == "success"
    sess = client._session_objs["session_99"]
    assert any("whoami" in w for w in sess.writes)
    assert sess.stopped is True


# ---------------------------------------------------------------------------
# T04: Connect failure propagates as structured failure reason
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t04_connect_failure_returns_structured_reason() -> None:
    """msfrpcd unreachable -> status=failed, reason exception text."""
    from app.config import settings

    engine = MetasploitRPCEngine()

    with patch.object(
        engine,
        "_connect",
        side_effect=ConnectionError("Connection refused"),
    ), patch.object(settings, "MOCK_METASPLOIT", False):
        result = await engine._run_exploit(
            "exploit/unix/ftp/vsftpd_234_backdoor",
            "cmd/unix/interact",
            {"RHOSTS": "192.168.0.26"},
        )

    assert result["status"] == "failed"
    assert result["engine"] == "metasploit"
    assert "refused" in result["reason"].lower()


@pytest.mark.asyncio
async def test_t04_no_session_within_timeout_returns_exploit_failed_reason() -> None:
    """Exploit runs but no session appears -> no-session reason with timeout."""
    from app.config import settings

    client = _StubClient()

    # exploit.execute returns normally, but no session is ever opened
    client.modules.use.return_value.execute = MagicMock()

    engine = MetasploitRPCEngine()

    with patch.object(engine, "_connect", return_value=client), \
         patch.object(settings, "MOCK_METASPLOIT", False), \
         patch.object(settings, "METASPLOIT_SESSION_WAIT_SEC", 2):
        result = await engine._run_exploit(
            "exploit/unix/ftp/vsftpd_234_backdoor",
            "cmd/unix/interact",
            {"RHOSTS": "192.168.0.26"},
        )

    assert result["status"] == "failed"
    assert "no session within" in result["reason"]
    assert "2s" in result["reason"]  # timeout was overridden to 2


# ---------------------------------------------------------------------------
# No session reuse: even if a stale session exists, it is not returned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_shot_does_not_reuse_pre_existing_session() -> None:
    """SPEC-053 invariant: pre-existing sessions are ignored.

    Before SPEC-053, _run_exploit walked sessions.list looking for
    target_host matches and returned a stale session if found. One-shot
    mode must NOT do that — it must always launch a fresh exploit.
    """
    from app.config import settings

    client = _StubClient()
    # Pre-plant a stale session for the same target
    stale = client.open_session("stale_01")

    # New exploit still opens fresh session
    def _exec_side_effect(*args, **kwargs):
        client.open_session("fresh_02")
        return MagicMock()

    client.modules.use.return_value.execute = MagicMock(side_effect=_exec_side_effect)

    engine = MetasploitRPCEngine()

    with patch.object(engine, "_connect", return_value=client), \
         patch.object(engine, "_read_shell_output", new=AsyncMock(return_value="ok")), \
         patch.object(settings, "MOCK_METASPLOIT", False):
        result = await engine._run_exploit(
            "exploit/unix/ftp/vsftpd_234_backdoor",
            "cmd/unix/interact",
            {"RHOSTS": "192.168.0.26"},
        )

    # The returned session must be the fresh one, not the stale one
    assert result["shell"] == "fresh_02", (
        "one-shot mode must not reuse pre-existing sessions"
    )
    assert stale.stopped is False, (
        "one-shot mode must not touch unrelated stale sessions"
    )
