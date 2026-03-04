# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""WinRMEngine — Windows Remote Management 命令執行引擎。

使用 pywinrm 連接 WinRM（TCP 5985/5986）執行 PowerShell 命令。
WINRM_ENABLED=false（預設）時，所有呼叫回傳 mock 成功結果。
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from app.clients import BaseEngineClient, ExecutionResult
from app.config import settings

logger = logging.getLogger(__name__)

# PowerShell 技術命令映射
WINRM_TECHNIQUE_EXECUTORS: dict[str, str] = {
    "T1021.001":    "whoami; hostname; ipconfig /all | Select-String 'IPv4'",
    "T1053.005":    "schtasks /query /fo CSV /nh 2>$null | Select-Object -First 10",
    "T1059.001":    "whoami; $env:COMPUTERNAME; Get-Process | Select-Object -First 5 Name,Id",
    "T1087.001":    "Get-LocalUser | Select-Object Name,Enabled,LastLogon",
    "T1083":        "Get-ChildItem C:\\Users -ErrorAction SilentlyContinue | Select-Object Name",
    "T1016":        "Get-NetIPAddress | Select-Object IPAddress,InterfaceAlias",
    "T1049":        "netstat -ano | Select-String 'LISTENING' | Select-Object -First 10",
}

# WinRM 認證格式：user:pass@host:port（port 預設 5985）
def _parse_winrm_credential(target: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' for WinRM. Port defaults to 5985."""
    try:
        userpass, hostport = target.rsplit("@", 1)
        username, password = userpass.split(":", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 5985
        return username, password, host, port
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid WinRM credential format: {exc}") from exc


class WinRMEngine(BaseEngineClient):
    """WinRM 命令執行引擎（pywinrm 包裝）。"""

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        execution_id = str(uuid.uuid4())
        command = WINRM_TECHNIQUE_EXECUTORS.get(ability_id, f"echo 'Unknown technique {ability_id}'")

        if not settings.WINRM_ENABLED:
            # Mock 模式
            mock_output = f"[MOCK WinRM] {ability_id} executed on {target}"
            return ExecutionResult(
                success=True,
                execution_id=execution_id,
                output=mock_output,
                facts=[{"trait": "host.os", "value": "Windows_Mock", "score": 1, "source": "winrm_mock"}],
            )

        try:
            username, password, host, port = _parse_winrm_credential(target)
            import winrm  # noqa: PLC0415  # pywinrm
            session = winrm.Session(
                f"http://{host}:{port}/wsman",
                auth=(username, password),
                transport="ntlm",
                read_timeout_sec=settings.WINRM_TIMEOUT_SEC,
                operation_timeout_sec=settings.WINRM_TIMEOUT_SEC,
            )
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: session.run_ps(command),
            )
            stdout = response.std_out.decode(errors="ignore").strip()
            stderr = response.std_err.decode(errors="ignore").strip()
            success = response.status_code == 0

            return ExecutionResult(
                success=success,
                execution_id=execution_id,
                output=stdout or stderr,
                facts=[{"trait": "host.os", "value": "Windows", "score": 1, "source": "winrm"}] if success else [],
                error=stderr if not success else None,
            )
        except Exception as exc:
            logger.warning("WinRM execution failed for %s: %s", target, exc)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=str(exc),
            )

    async def is_available(self) -> bool:
        return settings.WINRM_ENABLED
