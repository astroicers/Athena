# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Orient phase — PentestGPT integration, Athena's core value."""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone

import aiosqlite
import anthropic
import httpx

from app.config import settings
from app.ws_manager import WebSocketManager


def _to_camel_case(snake_str: str) -> str:
    """Convert snake_case string to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def _dict_to_camel_case(d: dict) -> dict:
    """Convert dict keys from snake_case to camelCase (shallow for recommendations)."""
    result = {}
    for key, value in d.items():
        camel_key = _to_camel_case(key)
        if isinstance(value, list):
            result[camel_key] = [
                _dict_to_camel_case(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[camel_key] = value
    return result

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
            "recommended_engine": "ssh",
            "confidence": 0.87,
            "prerequisites": ["SeDebugPrivilege (available)", "Local Admin (confirmed)"],
        },
        {
            "technique_id": "T1134",
            "technique_name": "Access Token Manipulation",
            "reasoning": "Stealthier approach using token impersonation, lower detection risk.",
            "risk_level": "low",
            "recommended_engine": "ssh",
            "confidence": 0.72,
            "prerequisites": ["SeImpersonatePrivilege"],
        },
        {
            "technique_id": "T1548.002",
            "technique_name": "Abuse Elevation Control: Bypass UAC",
            "reasoning": "UAC bypass on workstations for privilege escalation without credential dump.",
            "risk_level": "low",
            "recommended_engine": "c2",
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
- SSH Engine ("ssh"): standard execution via DirectSSH — default for most techniques.
- C2 Engine ("c2"): agent-based execution requiring a live C2 agent on target.
- Default to SSH Engine unless there is a specific reason for C2 Engine.
- When recommending techniques, PREFER techniques listed in AVAILABLE TECHNIQUE PLAYBOOKS (Section 7.6). Only suggest techniques outside that list if there is a compelling tactical reason.

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
      "recommended_engine": "ssh|c2",
      "confidence": 0.0-1.0,
      "prerequisites": ["list of prerequisites with verification status"]
    }
  ]
}
Provide exactly 3 options, ordered by confidence (highest first). \
When credential facts are available (category=credential), prioritize techniques that leverage \
those credentials for lateral movement before attempting new credential harvesting."""

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

## 7.5. HARVESTED CREDENTIALS (available for credential reuse)
{harvested_creds_str}

## 7.6. AVAILABLE TECHNIQUE PLAYBOOKS (executable via DirectSSHEngine)
{playbook_summary}

## 7.7. LATERAL MOVEMENT OPPORTUNITIES
{lateral_opportunities}

## 8. LATEST OBSERVE SUMMARY
{observe_summary}

Based on the above intelligence, provide your tactical analysis and 3 options as specified."""


class OrientEngine:
    """Orient phase — PentestGPT integration via LLM API."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager
        self._anthropic_client: anthropic.AsyncAnthropic | None = None
        self._oauth_manager = None  # lazy-init OAuthTokenManager

    async def analyze(
        self, db: aiosqlite.Connection, operation_id: str,
        observe_summary: str,
    ) -> dict:
        """Call LLM (or mock) to produce OrientRecommendation."""
        db.row_factory = aiosqlite.Row

        if settings.MOCK_LLM:
            rec = await self._store_recommendation(
                db, operation_id, _MOCK_RECOMMENDATION
            )
            await self._ws.broadcast(operation_id, "recommendation", _dict_to_camel_case(rec))
            return rec

        # Build prompt context (system + user)
        system_prompt, user_prompt = await self._build_prompt(
            db, operation_id, observe_summary
        )

        # Broadcast LLM call start for red team visibility
        backend_name = self._resolve_backend()
        await self._ws.broadcast(operation_id, "orient.thinking", {
            "status": "started",
            "backend": backend_name,
        })

        t0 = asyncio.get_event_loop().time()
        llm_response = await self._call_llm(system_prompt, user_prompt)
        latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

        # Broadcast LLM call completion with latency
        await self._ws.broadcast(operation_id, "orient.thinking", {
            "status": "completed",
            "backend": backend_name,
            "latency_ms": latency_ms,
        })

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
        await self._ws.broadcast(operation_id, "recommendation", _dict_to_camel_case(rec))
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

        # Q11: Harvested credentials for chaining context
        cred_cursor = await db.execute(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = ? AND category = 'credential' "
            "ORDER BY collected_at DESC LIMIT 10",
            (operation_id,),
        )
        cred_rows = await cred_cursor.fetchall()
        harvested_creds_str = (
            "\n".join(f"- {r['trait']}: {r['value'][:60]}" for r in cred_rows)
            if cred_rows
            else "None harvested yet."
        )

        # Q12: Available technique playbooks (ADR-018 Layer C)
        # Use active target for primary platform detection if set
        prim_tgt_cursor = await db.execute(
            "SELECT id, os FROM targets WHERE operation_id = ? AND is_active = 1 LIMIT 1",
            (operation_id,),
        )
        prim_tgt_row = await prim_tgt_cursor.fetchone()
        if not prim_tgt_row:
            prim_tgt_cursor = await db.execute(
                "SELECT id, os FROM targets WHERE operation_id = ? ORDER BY id LIMIT 1",
                (operation_id,),
            )
            prim_tgt_row = await prim_tgt_cursor.fetchone()
        target_os = (prim_tgt_row["os"] or "").lower() if prim_tgt_row else ""
        platform = "windows" if "windows" in target_os else "linux"
        primary_target_id = prim_tgt_row["id"] if prim_tgt_row else None

        pb_cursor = await db.execute(
            "SELECT mitre_id, tags FROM technique_playbooks "
            "WHERE platform = ? ORDER BY mitre_id",
            (platform,),
        )
        playbook_rows = await pb_cursor.fetchall()
        if playbook_rows:
            lines = []
            for row in playbook_rows:
                tags = json.loads(row["tags"] or "[]")
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                lines.append(f"- {row['mitre_id']}{tag_str} — available via DirectSSHEngine")
            playbook_summary = "\n".join(lines)
        else:
            playbook_summary = "(no playbooks registered)"

        # Section 7.7 — Lateral movement opportunities
        cred_cursor = await db.execute(
            "SELECT DISTINCT f.value, f.source_target_id, t.hostname, t.ip_address "
            "FROM facts f "
            "LEFT JOIN targets t ON t.id = f.source_target_id "
            "WHERE f.operation_id = ? AND f.trait = 'credential.ssh' "
            "LIMIT 10",
            (operation_id,),
        )
        cred_rows = await cred_cursor.fetchall()

        uncompromised_cursor = await db.execute(
            "SELECT id, hostname, ip_address, role, os "
            "FROM targets "
            "WHERE operation_id = ? AND (is_compromised = 0 OR is_compromised IS NULL) "
            "LIMIT 50",
            (operation_id,),
        )
        uncompromised_rows = await uncompromised_cursor.fetchall()

        if cred_rows and uncompromised_rows:
            cred_lines = [
                f"  - credential from {r['hostname'] or r['source_target_id'] or 'unknown'}: "
                f"{r['value'][:50]}..."
                for r in cred_rows
            ]
            target_lines = [
                f"  - {r['hostname']} ({r['ip_address']}) role={r['role']}"
                for r in uncompromised_rows
            ]
            lateral_str = (
                "Available SSH credentials:\n" + "\n".join(cred_lines) +
                "\n\nUncompromised targets:\n" + "\n".join(target_lines) +
                "\n\nConsider using T1021.004 (SSH) to move laterally "
                "from a compromised host to these targets."
            )
        else:
            lateral_str = "No lateral movement opportunities identified yet."

        # Query persistence facts for the primary target of this operation
        # (primary_target_id already resolved above alongside platform detection)
        if primary_target_id:
            persist_cursor = await db.execute(
                "SELECT DISTINCT value FROM facts "
                "WHERE operation_id = ? AND source_target_id = ? AND trait = 'host.persistence'",
                (operation_id, primary_target_id),
            )
            persist_rows = await persist_cursor.fetchall()
        else:
            persist_rows = []

        if persist_rows:
            persist_info = "Persistence vectors confirmed: " + ", ".join(
                r["value"] for r in persist_rows
            )
        else:
            persist_info = "No persistence established yet."
        lateral_str = lateral_str + f"\n\nPersistence status: {persist_info}"

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
            harvested_creds_str=harvested_creds_str,
            playbook_summary=playbook_summary,
            lateral_opportunities=lateral_str,
        )

        return _ORIENT_SYSTEM_PROMPT, user_prompt

    def _resolve_backend(self) -> str:
        """Determine which LLM backend to use: api_key, oauth, or none."""
        if settings.LLM_BACKEND != "auto":
            return settings.LLM_BACKEND
        if settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN:
            return "api_key"
        # Check OAuth credentials from Claude Code login
        from app.services.oauth_token_manager import OAuthTokenManager
        if self._oauth_manager is None:
            self._oauth_manager = OAuthTokenManager()
        if self._oauth_manager.is_available():
            return "oauth"
        return "api_key"  # will fall through to OpenAI or mock

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """LLM API call with dual-backend fallback (API Key / OAuth / OpenAI / mock)."""
        backend = self._resolve_backend()

        # Try Claude via API Key
        if backend == "api_key" and (settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN):
            try:
                return await self._call_claude(system_prompt, user_prompt)
            except Exception as e:
                logger.warning("Claude API Key failed: %s, trying fallback", e)

        # Try Claude via OAuth
        if backend in ("oauth", "auto"):
            try:
                return await self._call_claude_oauth(system_prompt, user_prompt)
            except Exception as e:
                logger.warning("Claude OAuth failed: %s, trying fallback", e)
                # If OAuth failed and API key is available, try that
                if backend == "oauth" and (settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN):
                    try:
                        return await self._call_claude(system_prompt, user_prompt)
                    except Exception as e2:
                        logger.warning("Claude API Key fallback also failed: %s", e2)

        # Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            try:
                return await self._call_openai(system_prompt, user_prompt)
            except Exception as e:
                logger.warning("OpenAI API failed: %s, using mock", e)

        logger.info("No LLM backend available, using mock recommendation")
        return json.dumps(_MOCK_RECOMMENDATION)

    async def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude API via official Anthropic SDK.

        Features over raw httpx:
        - Automatic retry with exponential backoff (default max_retries=2)
        - Typed error handling via anthropic exception hierarchy
        - Connection reuse via persistent AsyncAnthropic client
        """
        if self._anthropic_client is None:
            client_kwargs: dict = {"max_retries": 2}
            if settings.ANTHROPIC_API_KEY:
                client_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
            if settings.ANTHROPIC_AUTH_TOKEN:
                client_kwargs["auth_token"] = settings.ANTHROPIC_AUTH_TOKEN
            self._anthropic_client = anthropic.AsyncAnthropic(**client_kwargs)

        message = await self._anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=60.0,
        )

        if not message.content:
            raise ValueError("Empty content in Claude response")
        return message.content[0].text

    async def _call_claude_oauth(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude API using OAuth token from Claude Code credentials.

        Requires `anthropic-beta: oauth-2025-04-20` header for OAuth token auth.
        Uses a separate client instance to avoid header conflicts with API Key mode.
        """
        from app.services.oauth_token_manager import OAuthTokenManager, OAUTH_BETA_HEADER

        if self._oauth_manager is None:
            self._oauth_manager = OAuthTokenManager()

        token = await self._oauth_manager.get_access_token()

        # Use a dedicated client for OAuth (different headers from API Key client)
        client = anthropic.AsyncAnthropic(
            auth_token=token,
            max_retries=2,
            default_headers={"anthropic-beta": OAUTH_BETA_HEADER},
        )

        message = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=60.0,
        )

        if not message.content:
            raise ValueError("Empty content in Claude OAuth response")
        return message.content[0].text

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
