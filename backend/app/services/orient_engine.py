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

"""Orient phase — PentestGPT integration, Athena's core value."""

import json
import logging
import re
import uuid
from datetime import datetime, timezone

import aiosqlite
import httpx

from app.config import settings
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

# Mock recommendation matching SPEC-007 edge case requirements
_MOCK_RECOMMENDATION = {
    "situation_assessment": (
        "Target DC-01 runs Windows Server 2019 with SeDebugPrivilege available. "
        "Initial access established via WS-PC01. Agent AGENT-7F3A has SYSTEM on DC-01. "
        "Lateral movement options open to remaining hosts."
    ),
    "recommended_technique_id": "T1003.001",
    "confidence": 0.87,
    "reasoning_text": (
        "Target DC-01 runs Windows Server 2019 with SeDebugPrivilege available. "
        "LSASS process memory contains NTLM hashes for lateral movement. "
        "Credential access is the logical next step before expanding foothold."
    ),
    "options": [
        {
            "technique_id": "T1003.001",
            "technique_name": "OS Credential Dumping: LSASS Memory",
            "reasoning": "SeDebugPrivilege available on DC-01, direct LSASS dump for NTLM hashes.",
            "risk_level": "medium",
            "recommended_engine": "caldera",
            "confidence": 0.87,
            "prerequisites": ["SeDebugPrivilege (available)", "Local Admin (confirmed)"],
        },
        {
            "technique_id": "T1134",
            "technique_name": "Access Token Manipulation",
            "reasoning": "Stealthier approach using token impersonation, lower detection risk.",
            "risk_level": "low",
            "recommended_engine": "caldera",
            "confidence": 0.72,
            "prerequisites": ["SeImpersonatePrivilege"],
        },
        {
            "technique_id": "T1548.002",
            "technique_name": "Abuse Elevation Control: Bypass UAC",
            "reasoning": "UAC bypass on workstations for privilege escalation without credential dump.",
            "risk_level": "low",
            "recommended_engine": "shannon",
            "confidence": 0.65,
            "prerequisites": ["Local Admin on target workstation"],
        },
    ],
}

_ORIENT_PROMPT_TEMPLATE = """You are PentestGPT, an AI military intelligence advisor for cyber operations.

## Current Operation
- Strategic Intent: {strategic_intent}
- Status: {status}
- Current OODA Phase: Orient
- Threat Level: {threat_level}

## Completed Techniques
{completed_techniques}

## Failed Techniques
{failed_techniques}

## Available Targets
{targets}

## Agent Status
{agents}

## Latest Intelligence
{observe_summary}

## Your Task
Analyze the current situation and provide exactly 3 tactical options as JSON:
{{
  "situation_assessment": "brief situation analysis",
  "recommended_technique_id": "TXXXX.XXX",
  "confidence": 0.0-1.0,
  "reasoning_text": "detailed reasoning",
  "options": [
    {{
      "technique_id": "TXXXX.XXX",
      "technique_name": "Full Name",
      "reasoning": "why this technique now",
      "risk_level": "low|medium|high|critical",
      "recommended_engine": "caldera|shannon",
      "confidence": 0.0-1.0,
      "prerequisites": ["list of prerequisites"]
    }}
  ]
}}
Respond with ONLY valid JSON, no markdown or extra text."""


class OrientEngine:
    """Orient phase — PentestGPT integration via LLM API."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def analyze(
        self, db: aiosqlite.Connection, operation_id: str,
        observe_summary: str,
    ) -> dict:
        """Call LLM (or mock) to produce PentestGPTRecommendation."""
        db.row_factory = aiosqlite.Row

        if settings.MOCK_LLM:
            rec = await self._store_recommendation(
                db, operation_id, _MOCK_RECOMMENDATION
            )
            await self._ws.broadcast(operation_id, "recommendation", rec)
            return rec

        # Build prompt context
        prompt = await self._build_prompt(db, operation_id, observe_summary)

        # Call LLM
        llm_response = await self._call_llm(prompt)

        # Strip markdown code blocks if present (e.g. ```json ... ```)
        cleaned = llm_response.strip()
        md_match = re.match(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
        if md_match:
            cleaned = md_match.group(1).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON: %.200s", llm_response)
            parsed = _MOCK_RECOMMENDATION

        # Validate required fields
        _required = ("situation_assessment", "recommended_technique_id", "confidence", "options")
        if not all(k in parsed for k in _required):
            logger.warning(
                "LLM response missing required fields: %s",
                [k for k in _required if k not in parsed],
            )
            parsed = _MOCK_RECOMMENDATION
        elif not isinstance(parsed.get("options"), list) or len(parsed["options"]) < 1:
            logger.warning("LLM response has no valid options, falling back to mock")
            parsed = _MOCK_RECOMMENDATION

        rec = await self._store_recommendation(db, operation_id, parsed)
        await self._ws.broadcast(operation_id, "recommendation", rec)
        return rec

    async def _build_prompt(
        self, db: aiosqlite.Connection, operation_id: str, observe_summary: str
    ) -> str:
        # Get operation
        cursor = await db.execute(
            "SELECT * FROM operations WHERE id = ?", (operation_id,)
        )
        op = await cursor.fetchone()

        # Get completed techniques
        cursor = await db.execute(
            "SELECT te.technique_id, te.status, te.result_summary "
            "FROM technique_executions te WHERE te.operation_id = ? AND te.status = 'success'",
            (operation_id,),
        )
        completed = await cursor.fetchall()
        completed_str = "\n".join(
            f"- {r['technique_id']}: {r['result_summary'] or 'completed'}" for r in completed
        ) or "None yet"

        # Get failed techniques
        cursor = await db.execute(
            "SELECT te.technique_id, te.error_message "
            "FROM technique_executions te WHERE te.operation_id = ? AND te.status = 'failed'",
            (operation_id,),
        )
        failed = await cursor.fetchall()
        failed_str = "\n".join(
            f"- {r['technique_id']}: {r['error_message'] or 'failed'}" for r in failed
        ) or "None"

        # Get targets
        cursor = await db.execute(
            "SELECT hostname, ip_address, role, is_compromised, privilege_level "
            "FROM targets WHERE operation_id = ?", (operation_id,),
        )
        targets = await cursor.fetchall()
        targets_str = "\n".join(
            f"- {r['hostname']} ({r['ip_address']}) [{r['role']}] "
            f"{'COMPROMISED' if r['is_compromised'] else 'SECURE'} "
            f"{r['privilege_level'] or ''}"
            for r in targets
        ) or "No targets"

        # Get agents
        cursor = await db.execute(
            "SELECT paw, status, privilege, platform FROM agents WHERE operation_id = ?",
            (operation_id,),
        )
        agents = await cursor.fetchall()
        agents_str = "\n".join(
            f"- {r['paw']} [{r['status']}] {r['privilege']} ({r['platform']})"
            for r in agents
        ) or "No agents"

        return _ORIENT_PROMPT_TEMPLATE.format(
            strategic_intent=op["strategic_intent"] if op else "Unknown",
            status=op["status"] if op else "unknown",
            threat_level=op["threat_level"] if op else 0,
            completed_techniques=completed_str,
            failed_techniques=failed_str,
            targets=targets_str,
            agents=agents_str,
            observe_summary=observe_summary,
        )

    async def _call_llm(self, prompt: str) -> str:
        """LLM API call with dual-backend fallback."""
        # Try Claude first
        if settings.ANTHROPIC_API_KEY:
            try:
                return await self._call_claude(prompt)
            except Exception as e:
                logger.warning("Claude API failed: %s, trying OpenAI fallback", e)

        # Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            try:
                return await self._call_openai(prompt)
            except Exception as e:
                logger.warning("OpenAI API failed: %s, using mock", e)

        logger.info("No LLM API keys configured, using mock recommendation")
        return json.dumps(_MOCK_RECOMMENDATION)

    async def _call_claude(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2024-10-22",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.CLAUDE_MODEL,
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])
            if not content:
                raise ValueError("Empty content in Claude response")
            return content[0]["text"]

    async def _call_openai(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("Empty choices in OpenAI response")
            return choices[0]["message"]["content"]

    async def _store_recommendation(
        self, db: aiosqlite.Connection, operation_id: str, parsed: dict
    ) -> dict:
        """Store recommendation in DB and return as dict."""
        rec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Get current OODA iteration
        cursor = await db.execute(
            "SELECT id FROM ooda_iterations WHERE operation_id = ? "
            "ORDER BY iteration_number DESC LIMIT 1",
            (operation_id,),
        )
        row = await cursor.fetchone()
        ooda_iter_id = row["id"] if row else None

        options_json = json.dumps(parsed.get("options", []))
        await db.execute(
            "INSERT INTO recommendations "
            "(id, operation_id, ooda_iteration_id, situation_assessment, "
            "recommended_technique_id, confidence, options, reasoning_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rec_id, operation_id, ooda_iter_id,
                parsed.get("situation_assessment", ""),
                parsed.get("recommended_technique_id", ""),
                parsed.get("confidence", 0.0),
                options_json,
                parsed.get("reasoning_text", ""),
                now,
            ),
        )

        # Link recommendation to OODA iteration
        if ooda_iter_id:
            await db.execute(
                "UPDATE ooda_iterations SET recommendation_id = ? WHERE id = ?",
                (rec_id, ooda_iter_id),
            )

        await db.commit()

        return {
            "id": rec_id,
            "operation_id": operation_id,
            "ooda_iteration_id": ooda_iter_id,
            "situation_assessment": parsed.get("situation_assessment", ""),
            "recommended_technique_id": parsed.get("recommended_technique_id", ""),
            "confidence": parsed.get("confidence", 0.0),
            "options": parsed.get("options", []),
            "reasoning_text": parsed.get("reasoning_text", ""),
            "accepted": None,
            "created_at": now,
        }
