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

# ---------------------------------------------------------------------------
# MITRE ATT&CK kill chain stages (ordered)
# ---------------------------------------------------------------------------
_KILL_CHAIN_STAGES = [
    ("TA0043", "Reconnaissance"),
    ("TA0042", "Resource Development"),
    ("TA0001", "Initial Access"),
    ("TA0002", "Execution"),
    ("TA0003", "Persistence"),
    ("TA0004", "Privilege Escalation"),
    ("TA0005", "Defense Evasion"),
    ("TA0006", "Credential Access"),
    ("TA0007", "Discovery"),
    ("TA0008", "Lateral Movement"),
    ("TA0009", "Collection"),
    ("TA0011", "Command and Control"),
    ("TA0010", "Exfiltration"),
    ("TA0040", "Impact"),
]

# ---------------------------------------------------------------------------
# System prompt — static role contract + analytical framework (Pattern 2, 3)
# Inspired by: PentestGPT (MIT), hackingBuddyGPT (MIT), autopentest-ai (Apache 2.0)
# ---------------------------------------------------------------------------
_ORIENT_SYSTEM_PROMPT = """You are the Orient phase intelligence advisor for Athena C5ISR — \
a military-grade cyber operations command platform. Your role is STRICTLY advisory: \
analyze intelligence, recommend tactics, explain reasoning. You NEVER execute attacks.

## Analytical Framework

Apply these 5 rules to every analysis:

### 1. Kill Chain Reasoning (MITRE ATT&CK Progression)
Determine the current position in the ATT&CK kill chain:
TA0043 Reconnaissance → TA0042 Resource Development → TA0001 Initial Access → \
TA0002 Execution → TA0003 Persistence → TA0004 Privilege Escalation → \
TA0005 Defense Evasion → TA0006 Credential Access → TA0007 Discovery → \
TA0008 Lateral Movement → TA0009 Collection → TA0011 C2 → TA0010 Exfiltration → TA0040 Impact.
Identify where we are and what the logical next stage is. Do NOT skip stages without justification.

### 2. Dead Branch Pruning
When a technique has failed, infer the likely reason (e.g., EDR detected, privilege insufficient, \
service not running). Eliminate sibling techniques that share the same failure prerequisite. \
Recommend alternatives from a DIFFERENT tactic or approach vector.

### 3. Prerequisite Verification
Only recommend techniques whose prerequisites are CONFIRMED by collected intelligence. \
If a prerequisite is unverified, flag it and suggest a Discovery technique to verify it first.

### 4. Engine Routing
- Caldera: standard MITRE ATT&CK techniques with known ability mappings.
- Shannon: adaptive execution for unknown defenses, high-stealth requirements, or novel environments.
- Default to Caldera unless there is a specific reason for Shannon.

### 5. Risk Calibration
Assess risk based on DETECTION LIKELIHOOD, not just impact:
- low: passive/read-only, minimal footprint (e.g., registry reads, WMI queries)
- medium: active but common (e.g., LSASS dump with SeDebugPrivilege)
- high: noisy or easily signatured (e.g., PsExec lateral movement)
- critical: destructive or highly detectable (e.g., DCSync, data exfiltration)

## Output Contract
Respond with ONLY valid JSON (no markdown, no extra text). The JSON must match this schema exactly:
{
  "situation_assessment": "brief situation analysis citing kill chain position",
  "recommended_technique_id": "TXXXX.XXX",
  "confidence": 0.0-1.0,
  "reasoning_text": "detailed reasoning referencing collected intelligence",
  "options": [
    {
      "technique_id": "TXXXX.XXX",
      "technique_name": "Full MITRE Name",
      "reasoning": "why this technique NOW, citing prerequisites and intelligence",
      "risk_level": "low|medium|high|critical",
      "recommended_engine": "caldera|shannon",
      "confidence": 0.0-1.0,
      "prerequisites": ["list of prerequisites with verification status"]
    }
  ]
}
Provide exactly 3 options, ordered by confidence (highest first)."""

# ---------------------------------------------------------------------------
# User prompt template — dynamic context assembled per-call (8 sections)
# Inspired by: PentestGPT PTT (Pattern 1), PentAGI memory (Pattern 5),
#              hackingBuddyGPT reflection (Pattern 2), AttackGen grounding (Pattern 4)
# ---------------------------------------------------------------------------
_ORIENT_USER_PROMPT_TEMPLATE = """## 1. OPERATION BRIEF
- Codename: {codename}
- Strategic Intent: {strategic_intent}
- Status: {status}
- Threat Level: {threat_level}
- Automation Mode: {automation_mode}
- Risk Threshold: {risk_threshold}

## 2. MISSION TASK TREE
{task_tree}

## 3. KILL CHAIN POSITION
Executed Tactics: {executed_tactics}
Current Stage: {current_stage}
Next Logical Stage: {next_stage}

## 4. OPERATIONAL HISTORY (recent OODA cycles)
{ooda_history}

## 5. PREVIOUS ASSESSMENTS
{previous_assessments}

## 6. CATEGORIZED INTELLIGENCE
{categorized_facts}

## 7. ASSET STATUS

### Targets
{targets}

### Completed Techniques
{completed_techniques}

### Failed Techniques
{failed_techniques}

### Active Agents
{agents}

## 8. LATEST OBSERVE SUMMARY
{observe_summary}

Based on the above intelligence, provide your tactical analysis and 3 options as specified."""


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

        # Build prompt context (system + user)
        system_prompt, user_prompt = await self._build_prompt(
            db, operation_id, observe_summary
        )

        # Call LLM
        llm_response = await self._call_llm(system_prompt, user_prompt)

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

    # ------------------------------------------------------------------
    # Prompt formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_task_tree(rows) -> str:
        if not rows:
            return "No mission steps defined."
        lines = []
        for r in rows:
            status_icon = {"completed": "[x]", "running": "[>]", "failed": "[!]"}.get(
                r["status"], "[ ]"
            )
            lines.append(
                f"  {r['step_number']}. {status_icon} {r['technique_name']} "
                f"({r['technique_id']}) → {r['target_label']} [{r['engine']}]"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_ooda_history(rows) -> str:
        if not rows:
            return "First iteration — no prior cycles."
        lines = []
        for r in rows:
            lines.append(
                f"- Cycle #{r['iteration_number']}: "
                f"Observe={r['observe_summary'] or 'n/a'} | "
                f"Act={r['act_summary'] or 'n/a'}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_previous_assessments(rows) -> str:
        if not rows:
            return "No prior assessments."
        lines = []
        for r in rows:
            lines.append(
                f"- Recommended {r['recommended_technique_id']}: "
                f"{r['situation_assessment'][:120]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_categorized_facts(rows) -> str:
        if not rows:
            return "No intelligence collected yet."
        by_cat: dict[str, list[str]] = {}
        for r in rows:
            cat = r["category"].upper()
            by_cat.setdefault(cat, []).append(f"  - {r['trait']}: {r['value']}")
        lines = []
        for cat, items in by_cat.items():
            lines.append(f"### {cat} INTELLIGENCE")
            lines.extend(items[:5])  # limit per category
        return "\n".join(lines)

    @staticmethod
    def _infer_kill_chain_stage(executed_tactic_ids: list[str]) -> tuple[str, str]:
        """Return (current_stage, next_stage) based on executed tactics."""
        if not executed_tactic_ids:
            return "Pre-engagement (no tactics executed)", _KILL_CHAIN_STAGES[0][1]

        # Find the furthest executed stage
        max_idx = -1
        for tid in executed_tactic_ids:
            for idx, (stage_id, _) in enumerate(_KILL_CHAIN_STAGES):
                if stage_id == tid and idx > max_idx:
                    max_idx = idx

        if max_idx < 0:
            return "Unknown (tactics not in kill chain)", _KILL_CHAIN_STAGES[0][1]

        current = f"{_KILL_CHAIN_STAGES[max_idx][1]} ({_KILL_CHAIN_STAGES[max_idx][0]})"
        next_idx = min(max_idx + 1, len(_KILL_CHAIN_STAGES) - 1)
        next_stage = f"{_KILL_CHAIN_STAGES[next_idx][1]} ({_KILL_CHAIN_STAGES[next_idx][0]})"
        return current, next_stage

    # ------------------------------------------------------------------
    # Build prompt — returns (system_prompt, user_prompt) tuple
    # ------------------------------------------------------------------

    async def _build_prompt(
        self, db: aiosqlite.Connection, operation_id: str, observe_summary: str
    ) -> tuple[str, str]:
        # --- Existing queries (preserved) ---

        # Q1: Operation details
        cursor = await db.execute(
            "SELECT * FROM operations WHERE id = ?", (operation_id,)
        )
        op = await cursor.fetchone()

        # Q2: Completed techniques
        cursor = await db.execute(
            "SELECT te.technique_id, te.status, te.result_summary "
            "FROM technique_executions te WHERE te.operation_id = ? AND te.status = 'success'",
            (operation_id,),
        )
        completed = await cursor.fetchall()
        completed_str = "\n".join(
            f"- {r['technique_id']}: {r['result_summary'] or 'completed'}" for r in completed
        ) or "None yet"

        # Q3: Failed techniques
        cursor = await db.execute(
            "SELECT te.technique_id, te.error_message "
            "FROM technique_executions te WHERE te.operation_id = ? AND te.status = 'failed'",
            (operation_id,),
        )
        failed = await cursor.fetchall()
        failed_str = "\n".join(
            f"- {r['technique_id']}: {r['error_message'] or 'failed'}" for r in failed
        ) or "None"

        # Q4: Targets (enriched with os, network_segment)
        cursor = await db.execute(
            "SELECT hostname, ip_address, os, role, network_segment, "
            "is_compromised, privilege_level "
            "FROM targets WHERE operation_id = ?", (operation_id,),
        )
        targets = await cursor.fetchall()
        targets_str = "\n".join(
            f"- {r['hostname']} ({r['ip_address']}) [{r['role']}] "
            f"OS={r['os'] or 'unknown'} Net={r['network_segment'] or 'unknown'} "
            f"{'COMPROMISED' if r['is_compromised'] else 'SECURE'} "
            f"{r['privilege_level'] or ''}"
            for r in targets
        ) or "No targets"

        # Q5: Agents
        cursor = await db.execute(
            "SELECT paw, status, privilege, platform FROM agents WHERE operation_id = ?",
            (operation_id,),
        )
        agents = await cursor.fetchall()
        agents_str = "\n".join(
            f"- {r['paw']} [{r['status']}] {r['privilege']} ({r['platform']})"
            for r in agents
        ) or "No agents"

        # --- New queries (Pattern 1, 4, 5) ---

        # Q6: Mission task tree (Pattern 1 — PTT)
        cursor = await db.execute(
            "SELECT step_number, technique_name, status, technique_id, engine, target_label "
            "FROM mission_steps WHERE operation_id = ? ORDER BY step_number ASC",
            (operation_id,),
        )
        mission_steps = await cursor.fetchall()
        task_tree_str = self._format_task_tree(mission_steps)

        # Q7: OODA history — compressed working memory (Pattern 5)
        cursor = await db.execute(
            "SELECT iteration_number, observe_summary, act_summary, completed_at "
            "FROM ooda_iterations WHERE operation_id = ? "
            "ORDER BY iteration_number DESC LIMIT 3",
            (operation_id,),
        )
        ooda_history = await cursor.fetchall()
        ooda_history_str = self._format_ooda_history(ooda_history)

        # Q8: Previous assessments — episodic memory (Pattern 5)
        cursor = await db.execute(
            "SELECT situation_assessment, recommended_technique_id, reasoning_text "
            "FROM recommendations WHERE operation_id = ? "
            "ORDER BY created_at DESC LIMIT 2",
            (operation_id,),
        )
        prev_assessments = await cursor.fetchall()
        prev_assessments_str = self._format_previous_assessments(prev_assessments)

        # Q9: Kill chain tactic progression (Pattern 4)
        cursor = await db.execute(
            "SELECT DISTINCT t.tactic, t.tactic_id "
            "FROM technique_executions te JOIN techniques t ON te.technique_id = t.mitre_id "
            "WHERE te.operation_id = ? AND te.status = 'success'",
            (operation_id,),
        )
        tactic_rows = await cursor.fetchall()
        executed_tactic_ids = [r["tactic_id"] for r in tactic_rows]
        executed_tactics_str = ", ".join(
            f"{r['tactic']} ({r['tactic_id']})" for r in tactic_rows
        ) or "None yet"
        current_stage, next_stage = self._infer_kill_chain_stage(executed_tactic_ids)

        # Q10: Categorized facts (Pattern 2 — reflection)
        cursor = await db.execute(
            "SELECT category, trait, value FROM facts "
            "WHERE operation_id = ? ORDER BY category, collected_at DESC LIMIT 30",
            (operation_id,),
        )
        facts = await cursor.fetchall()
        categorized_facts_str = self._format_categorized_facts(facts)

        # --- Assemble user prompt ---
        user_prompt = _ORIENT_USER_PROMPT_TEMPLATE.format(
            codename=op["codename"] if op else "Unknown",
            strategic_intent=op["strategic_intent"] if op else "Unknown",
            status=op["status"] if op else "unknown",
            threat_level=op["threat_level"] if op else 0,
            automation_mode=op["automation_mode"] if op else "semi_auto",
            risk_threshold=op["risk_threshold"] if op else "medium",
            task_tree=task_tree_str,
            executed_tactics=executed_tactics_str,
            current_stage=current_stage,
            next_stage=next_stage,
            ooda_history=ooda_history_str,
            previous_assessments=prev_assessments_str,
            categorized_facts=categorized_facts_str,
            targets=targets_str,
            completed_techniques=completed_str,
            failed_techniques=failed_str,
            agents=agents_str,
            observe_summary=observe_summary,
        )

        return _ORIENT_SYSTEM_PROMPT, user_prompt

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """LLM API call with dual-backend fallback."""
        # Try Claude first
        if settings.ANTHROPIC_API_KEY:
            try:
                return await self._call_claude(system_prompt, user_prompt)
            except Exception as e:
                logger.warning("Claude API failed: %s, trying OpenAI fallback", e)

        # Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            try:
                return await self._call_openai(system_prompt, user_prompt)
            except Exception as e:
                logger.warning("OpenAI API failed: %s, using mock", e)

        logger.info("No LLM API keys configured, using mock recommendation")
        return json.dumps(_MOCK_RECOMMENDATION)

    async def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
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
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])
            if not content:
                raise ValueError("Empty content in Claude response")
            return content[0]["text"]

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
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
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
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
