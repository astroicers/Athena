# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Act phase — route execution to Caldera or Shannon engine."""

import logging
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.clients import BaseEngineClient, ExecutionResult
from app.services.fact_collector import FactCollector
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)


class EngineRouter:
    """Act phase: route technique execution to the appropriate engine."""

    def __init__(
        self,
        caldera: BaseEngineClient,
        shannon: BaseEngineClient | None,
        fact_collector: FactCollector,
        ws_manager: WebSocketManager,
    ):
        self._caldera = caldera
        self._shannon = shannon
        self._fact_collector = fact_collector
        self._ws = ws_manager

    async def execute(
        self, db: aiosqlite.Connection, technique_id: str, target_id: str,
        engine: str, operation_id: str, ooda_iteration_id: str | None = None,
    ) -> dict:
        """
        Execute a technique via the selected engine:
        1. Create TechniqueExecution record (status=running)
        2. Call CalderaClient / ShannonClient
        3. Update status (success/failed)
        4. Extract facts from result
        5. Push WebSocket execution.update event
        """
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Get the technique's caldera_ability_id
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT mitre_id, caldera_ability_id FROM techniques WHERE mitre_id = ?",
            (technique_id,),
        )
        tech_row = await cursor.fetchone()
        ability_id = (tech_row["caldera_ability_id"] if tech_row else None) or technique_id

        # Get target paw/hostname for engine
        cursor = await db.execute(
            "SELECT hostname FROM targets WHERE id = ?", (target_id,)
        )
        target_row = await cursor.fetchone()
        target_label = target_row["hostname"] if target_row else target_id

        # Create execution record
        await db.execute(
            "INSERT INTO technique_executions "
            "(id, technique_id, target_id, operation_id, ooda_iteration_id, "
            "engine, status, started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (exec_id, technique_id, target_id, operation_id,
             ooda_iteration_id, engine, now),
        )
        await db.commit()

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": "running", "engine": engine,
        })

        # Select and call engine
        client = self._select_client(engine)
        result: ExecutionResult = await client.execute(ability_id, target_label)

        # Update execution record
        completed_at = datetime.now(timezone.utc).isoformat()
        status = "success" if result.success else "failed"
        facts_count = len(result.facts)

        await db.execute(
            "UPDATE technique_executions SET status = ?, result_summary = ?, "
            "facts_collected_count = ?, completed_at = ?, error_message = ? "
            "WHERE id = ?",
            (status, result.output, facts_count, completed_at,
             result.error, exec_id),
        )

        # [I-1] Only increment techniques_executed on success
        if result.success:
            await db.execute(
                "UPDATE operations SET techniques_executed = techniques_executed + 1 "
                "WHERE id = ?",
                (operation_id,),
            )
        await db.commit()

        # Extract facts from result
        if result.facts:
            await self._fact_collector.collect_from_result(
                db, operation_id, technique_id, target_id, result.facts
            )

        await self._ws.broadcast(operation_id, "execution.update", {
            "id": exec_id, "technique_id": technique_id,
            "status": status, "engine": engine,
            "facts_collected": facts_count,
        })

        return {
            "execution_id": exec_id,
            "technique_id": technique_id,
            "target_id": target_id,
            "engine": engine,
            "status": status,
            "result_summary": result.output,
            "facts_collected_count": facts_count,
            "error": result.error,
        }

    def select_engine(
        self, technique_id: str, context: dict,
        gpt_recommendation: str | None = None,
    ) -> str:
        """
        Engine selection logic per ADR-006 priority order:
        1. High-confidence PentestGPT recommendation → trust its engine choice
        2. Caldera has corresponding ability → Caldera
        3. Unknown environment + Shannon available → Shannon
        4. High stealth requirement + Shannon available → Shannon
        5. Default → Caldera
        """
        # Priority 1: Trust high-confidence PentestGPT recommendation
        if gpt_recommendation and gpt_recommendation in ("caldera", "shannon"):
            if gpt_recommendation == "shannon" and self._shannon:
                return "shannon"
            return "caldera"

        # Priority 2: Caldera has ability for this technique (always true for known MITRE IDs)
        # In POC, Caldera is assumed to have all standard MITRE abilities
        # A production version would check caldera.list_abilities()

        # Priority 3: Unknown environment → Shannon
        if context.get("environment") == "unknown" and self._shannon:
            return "shannon"

        # Priority 4: High stealth requirement → Shannon
        if context.get("stealth_level") == "maximum" and self._shannon:
            return "shannon"

        # Priority 5: Default → Caldera (most reliable)
        return "caldera"

    def _select_client(self, engine: str) -> BaseEngineClient:
        if engine == "shannon" and self._shannon:
            return self._shannon
        return self._caldera
