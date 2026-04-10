# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Orient phase — PentestGPT integration, Athena's core value."""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone

import asyncpg

from app.config import settings
from app.services.mission_profile_loader import get_profile, noise_allowed, NOISE_RANKS
from app.ws_manager import WebSocketManager


def _to_camel_case(snake_str: str) -> str:
    """Convert snake_case string to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def _format_relay_infrastructure() -> str:
    """SPEC-054: Build the Section 7.9 Infrastructure block for Orient.

    Pure function so it can be unit-tested without spinning up the
    whole ``OrientEngine``. Reads ``settings.RELAY_IP`` and emits a
    short block that tells the LLM whether reverse-shell exploits are
    viable on this Athena deployment.

    The key `relay_available: true|false` is intentionally spelled as
    a single underscored token so the prompt matches the LLM-facing
    Rule #8/#9 text that references `relay_available`.
    """
    relay_ip = getattr(settings, "RELAY_IP", "") or ""
    available = bool(relay_ip)
    if available:
        return (
            "- relay_available: true\n"
            f"- Relay LHOST: {relay_ip}\n"
            "- Reverse shell exploits viable: true\n"
            "- Permitted exploit classes: bind shell, reverse shell, "
            "credential-based"
        )
    return (
        "- relay_available: false\n"
        "- Relay LHOST: (none)\n"
        "- Reverse shell exploits viable: false\n"
        "- Permitted exploit classes: bind shell (vsftpd), "
        "credential-based (T1110.*, T1078.*)\n"
        "- AVOID: reverse-shell exploits (UnrealIRCd, Samba usermap, "
        "distccd) because target cannot call back to Athena"
    )


def _dict_to_camel_case(d: dict) -> dict:
    """Convert dict keys from snake_case to camelCase (shallow for recommendations)."""
    from datetime import datetime as _dt

    result = {}
    for key, value in d.items():
        camel_key = _to_camel_case(key)
        if isinstance(value, list):
            result[camel_key] = [
                _dict_to_camel_case(item) if isinstance(item, dict)
                else item.isoformat() if isinstance(item, _dt)
                else item
                for item in value
            ]
        elif isinstance(value, _dt):
            result[camel_key] = value.isoformat()
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
            "technique_id": "T1558.003",
            "technique_name": "Steal or Forge Kerberos Tickets: Kerberoasting",
            "reasoning": "AD environment with SPN-enabled service accounts -- Kerberoasting extracts TGS tickets.",
            "risk_level": "medium",
            "recommended_engine": "winrm",
            "confidence": 0.65,
            "prerequisites": ["Domain user access", "AD environment"],
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
# System prompt -- static role contract + analytical framework (Pattern 2, 3)
# Inspired by: PentestGPT (MIT), hackingBuddyGPT (MIT), autopentest-ai (Apache 2.0)
# ---------------------------------------------------------------------------
_ORIENT_SYSTEM_PROMPT = """You are the Orient phase intelligence advisor for Athena C5ISR -- \
a military-grade cyber operations command platform. Your role is STRICTLY advisory: \
analyze intelligence, recommend tactics, explain reasoning. You NEVER execute attacks.

## Analytical Framework

Apply these 8 rules to every analysis:

### 1. Kill Chain Reasoning (MITRE ATT&CK Progression)
Determine the current position in the ATT&CK kill chain:
TA0043 Reconnaissance -> TA0042 Resource Development -> TA0001 Initial Access -> \
TA0002 Execution -> TA0003 Persistence -> TA0004 Privilege Escalation -> \
TA0005 Defense Evasion -> TA0006 Credential Access -> TA0007 Discovery -> \
TA0008 Lateral Movement -> TA0009 Collection -> TA0011 C2 -> TA0010 Exfiltration -> TA0040 Impact.
Identify where we are and what the logical next stage is. Do NOT skip stages without justification.

### 2. Dead Branch Pruning
When a technique has failed, infer the likely reason (e.g., EDR detected, privilege insufficient, \
service not running). Eliminate sibling techniques that share the same failure prerequisite. \
Recommend alternatives from a DIFFERENT tactic or approach vector.

### 3. Prerequisite Verification
Only recommend techniques whose prerequisites are CONFIRMED by collected intelligence. \
If a prerequisite is unverified, flag it and suggest a Discovery technique to verify it first.

### 4. Engine Routing
- SSH Engine ("ssh"): standard execution via DirectSSH -- default for most techniques.
- C2 Engine ("c2"): agent-based execution requiring a live C2 agent on target.
{mcp_engine_section}\
- Default to SSH Engine unless there is a specific reason for C2{mcp_or_note} Engine.
- When recommending techniques, PREFER techniques listed in AVAILABLE TECHNIQUE PLAYBOOKS (Section 7.6). Only suggest techniques outside that list if there is a compelling tactical reason.

### 5. Risk Calibration
Assess risk based on DETECTION LIKELIHOOD, not just impact:
- low: passive/read-only, minimal footprint (e.g., registry reads, WMI queries)
- medium: active but common (e.g., LSASS dump with SeDebugPrivilege)
- high: noisy or easily signatured (e.g., PsExec lateral movement)
- critical: destructive or highly detectable (e.g., DCSync, data exfiltration)

### 6. No Redundant Recommendations
NEVER recommend a technique that already appears in Section 7 "Completed Techniques". \
Those techniques have already been executed successfully. Instead, recommend the NEXT logical \
technique in the kill chain that builds on the results of completed techniques. \
If a technique was completed on Target A but not on Target B, you MAY recommend it for Target B.

### 7. Attack Graph Awareness
When Section 10 contains an attack graph summary with a recommended_path, PRIORITIZE techniques \
on that path. The attack graph represents validated prerequisite chains — following it reduces \
risk of skipping critical steps. If the graph shows a technique with EXPLORED status, treat it \
as already completed. UNREACHABLE nodes should be avoided unless you have new intelligence that \
changes their feasibility.

### 8. Recon-to-Initial Access Transition (SPEC-052, relaxed by SPEC-053)
When the intelligence shows:
- service.open_port facts with SSH (port 22), RDP (port 3389), WinRM (port 5985/5986), or FTP (port 21)
- No credential facts yet exist for those services (no credential.ssh, credential.rdp, credential.winrm)
- Kill chain position is at TA0043 (Reconnaissance) or TA0007 (Discovery)

Then you SHOULD recommend Initial Access techniques as the natural next step:
- T1110.001 (Brute Force: Password Guessing) for SSH/RDP/WinRM services
- T1078.001 (Valid Accounts: Default Accounts) if default credentials are likely (IoT, dev environments)
- T1190 (Exploit Public-Facing Application) when a service banner matches a known exploitable
  signature (e.g. "vsftpd 2.3.4", "UnrealIRCd", "samba 3.0", "distccd"). A CVE fact is NOT required
  — the banner substring is sufficient evidence. Prefer engine="metasploit" for T1190.

This is the natural Kill Chain progression from Reconnaissance (TA0043) to Initial Access (TA0001).
Do NOT skip this step — establishing initial access is prerequisite for all post-exploitation techniques.

**Relay-aware exploit selection (SPEC-054, ADR-047):** Before recommending any reverse-shell
exploit, consult Section 7.9 "INFRASTRUCTURE". If `relay_available: false`, AVOID the following
reverse-shell exploits because the target cannot call back to Athena across the network boundary:

  - `exploit/unix/irc/unreal_ircd_3281_backdoor` (UnrealIRCd)
  - `exploit/multi/samba/usermap_script` (Samba usermap)
  - `exploit/unix/misc/distcc_exec` (distccd)
  - Any Metasploit module whose payload is `cmd/unix/reverse` or variants

When `relay_available: false`, prefer instead:

  - **Bind shell exploits**: `exploit/unix/ftp/vsftpd_234_backdoor` (vsftpd 2.3.4) — target opens
    a listener on port 6200, Athena connects outbound
  - **Credential-based techniques**: T1110.001 (Brute Force), T1078.001 (Valid Accounts), etc.
  - **Discovery techniques**: T1046, T1018, T1087 to enumerate alternative attack surfaces

When `relay_available: true` with a specific `Relay LHOST` set, reverse-shell exploits become
viable — Metasploit's LHOST is injected from `settings.RELAY_IP` automatically, so you may
recommend them normally.

### 9. Initial Access Exhausted → Exploit Pivot (SPEC-053, ADR-046, extended by SPEC-054)
When Section 7 "Failed Techniques" contains an entry with the `[auth_failure]` category for
an Initial Access technique (T1110.*, T1078.*) on a target, AND that target has a
`service.open_port` fact whose value matches any known exploitable banner signature
(vsftpd_2.3.4, unrealircd, samba 3.0, distccd, or similar), THEN you MUST recommend T1190
(Exploit Public-Facing Application) on that target with engine="metasploit".

**SPEC-054 relay_available condition:** The specific T1190 sub-variant depends on Section 7.9:

  - If `relay_available: true`: you may recommend the reverse-shell variant
    (samba/UnrealIRCd/distccd) matching the target banner
  - If `relay_available: false`: recommend ONLY the bind-shell variant
    (vsftpd_2.3.4) if the target banner includes vsftpd 2.3.4. If the only exploitable
    banners are reverse-shell class (e.g. Samba/UnrealIRCd without vsftpd), flag the target
    path as blocked and recommend a Discovery technique instead

Reasoning: credential-based initial access has been exhausted on that target. The kill chain
cannot progress via credentials, so pivot to exploit-based initial access using the detected
vulnerable banner. Do NOT retry T1110 on the same target in the same iteration — it will
deterministically fail again. Only retry T1110 after new credentials are harvested elsewhere.

This rule is an EXPLICIT EXCEPTION to Rule #6 (No Redundant Recommendations). T1190 may be
recommended on a target where T1110 previously failed, and this is NOT a redundancy — it is
the correct cross-category pivot. Record the pivot reasoning in `situation_assessment` so
the Timeline can show it as an AI decision, not a silent fallback.

If no exploitable banner is present on the failed target, do NOT recommend T1190 on that
target. Instead recommend a Discovery technique to enumerate alternative attack surfaces
(T1046 Network Service Discovery on adjacent hosts, T1018 Remote System Discovery, etc.)
or flag the target path as blocked.

## Output Contract
Respond with ONLY valid JSON (no markdown, no extra text). The JSON must match this schema exactly:
{{
  "situation_assessment": "brief situation analysis citing kill chain position",
  "recommended_technique_id": "TXXXX.XXX",
  "confidence": 0.0-1.0,
  "reasoning_text": "detailed reasoning referencing collected intelligence",
  "options": [
    {{
      "technique_id": "TXXXX.XXX",
      "technique_name": "Full MITRE Name",
      "reasoning": "why this technique NOW, citing prerequisites and intelligence",
      "risk_level": "low|medium|high|critical",
      "recommended_engine": "ssh|c2|mcp|metasploit",
      "confidence": 0.0-1.0,
      "prerequisites": ["list of prerequisites with verification status"]
    }}
  ]
}}
Provide exactly 3 options, ordered by confidence (highest first). \
When credential facts are available (category=credential), prioritize techniques that leverage \
those credentials for lateral movement before attempting new credential harvesting.

Engine selection guide:
- "ssh": Execute commands via SSH on a compromised host (requires valid credential.ssh fact)
{mcp_engine_guide}
- "metasploit": Exploit vulnerable services (vsftpd backdoor, Samba RCE, etc.) -- use when a known-exploitable service is detected in service.open_port facts and you need to gain initial/root access WITHOUT existing credentials
- "c2": Use C2 agent for stealth operations

IMPORTANT: When access is lost or no valid credentials exist, use "metasploit" engine to exploit vulnerable network services (e.g., vsftpd 2.3.4, Samba 3.X, UnrealIRCd) for direct root shell access."""

# ---------------------------------------------------------------------------
# User prompt template -- dynamic context assembled per-call (8 sections)
# Inspired by: PentestGPT PTT (Pattern 1), PentAGI memory (Pattern 5),
#              hackingBuddyGPT reflection (Pattern 2), AttackGen grounding (Pattern 4)
# ---------------------------------------------------------------------------
_ORIENT_USER_PROMPT_TEMPLATE = """## 1. OPERATION BRIEF
- Codename: {codename}
- Strategic Intent: {strategic_intent}
- Status: {status}
- Mission Profile: {mission_profile} ({mission_profile_name})
- Max Noise Allowed: {max_noise}
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

## 7.8. AVAILABLE MCP TOOLS (stateless query tools)
{mcp_tools_summary}

## 7.9. INFRASTRUCTURE (SPEC-054 relay awareness)
{relay_infrastructure}

## 8. LATEST OBSERVE SUMMARY
{observe_summary}

## 8.9. OPSEC STATUS
- Detection Risk: {opsec_detection_risk}%
- Noise Budget Remaining: {opsec_noise_budget_remaining} pts
- Exposure Count: {opsec_exposure_count}

## 10. ATTACK GRAPH STATUS
{attack_graph_summary}

## 11. KNOWN VULNERABILITIES
{known_vulnerabilities}

Based on the above intelligence, provide your tactical analysis and 3 options as specified."""


class OrientEngine:
    """Orient phase -- PentestGPT integration via LLM API."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def analyze(
        self, db: asyncpg.Connection, operation_id: str,
        observe_summary: str, *, attack_graph_summary: str = "",
    ) -> dict:
        """Call LLM (or mock) to produce OrientRecommendation."""

        # Read mission profile for noise filtering
        op_row = await db.fetchrow(
            "SELECT mission_profile FROM operations WHERE id = $1", operation_id,
        )
        mission_code = (op_row["mission_profile"] if op_row else None) or "SP"

        if settings.MOCK_LLM:
            filtered_mock = await self._filter_options_by_noise(
                db, _MOCK_RECOMMENDATION, mission_code,
            )
            rec = await self._store_recommendation(
                db, operation_id, filtered_mock
            )
            await self._ws.broadcast(operation_id, "recommendation", _dict_to_camel_case(rec))
            return rec

        # Build prompt context (system + user)
        system_prompt, user_prompt = await self._build_prompt(
            db, operation_id, observe_summary,
            attack_graph_summary=attack_graph_summary,
        )

        # Broadcast LLM call start for red team visibility
        from app.services.llm_client import get_llm_client
        client = get_llm_client()
        backend_name = client._resolve_backend() if client else "mock"
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
            logger.error("Orient LLM returned non-JSON: %.200s", llm_response)
            if settings.MOCK_LLM:
                parsed = _MOCK_RECOMMENDATION
            else:
                await self._ws.broadcast(operation_id, "orient.error",
                    {"error": "LLM returned non-JSON"})
                return {}

        # Validate required fields
        _required = ("situation_assessment", "recommended_technique_id", "confidence", "options")
        if not all(k in parsed for k in _required):
            logger.error(
                "Orient LLM response missing required fields: %s",
                [k for k in _required if k not in parsed],
            )
            if settings.MOCK_LLM:
                parsed = _MOCK_RECOMMENDATION
            else:
                return {}
        elif not isinstance(parsed.get("options"), list) or len(parsed["options"]) < 1:
            logger.error("Orient LLM response has no valid options")
            if settings.MOCK_LLM:
                parsed = _MOCK_RECOMMENDATION
            else:
                return {}

        # SPEC-046: Filter options exceeding mission noise limit
        parsed = await self._filter_options_by_noise(db, parsed, mission_code)

        rec = await self._store_recommendation(db, operation_id, parsed)
        await self._ws.broadcast(operation_id, "recommendation", _dict_to_camel_case(rec))
        return rec

    # ------------------------------------------------------------------
    # SPEC-046: Noise-level filtering
    # ------------------------------------------------------------------

    async def _filter_options_by_noise(
        self, db: asyncpg.Connection, parsed: dict, mission_code: str,
    ) -> dict:
        """Remove options whose technique noise_level exceeds the mission limit.

        Looks up each option's technique_id in the techniques table to get its
        noise_level, then filters using the mission profile's max_noise setting.
        """
        profile = get_profile(mission_code)
        max_noise = profile.get("max_noise", "high")
        if max_noise == "all":
            return parsed  # FA mode — no filtering

        options = parsed.get("options", [])
        if not options:
            return parsed

        # Batch-fetch noise levels for all technique_ids in options
        tech_ids = [o.get("technique_id", "") for o in options]
        rows = await db.fetch(
            "SELECT mitre_id, noise_level FROM techniques WHERE mitre_id = ANY($1)",
            tech_ids,
        )
        noise_map = {r["mitre_id"]: r["noise_level"] or "medium" for r in rows}

        filtered = []
        for opt in options:
            tid = opt.get("technique_id", "")
            tech_noise = noise_map.get(tid, "medium")
            if NOISE_RANKS.get(tech_noise, 2) <= NOISE_RANKS.get(max_noise, 3):
                filtered.append(opt)
            else:
                logger.info(
                    "SPEC-046: Excluded technique %s (noise=%s) for mission %s (max=%s)",
                    tid, tech_noise, mission_code, max_noise,
                )

        if not filtered:
            # All options exceeded noise limit — keep only the lowest-noise one
            lowest = min(
                options,
                key=lambda o: NOISE_RANKS.get(
                    noise_map.get(o.get("technique_id", ""), "medium"), 2
                ),
            )
            lowest["noise_override"] = True
            logger.warning(
                "All Orient options exceeded noise limit for %s — "
                "falling back to lowest-noise option %s (needs confirmation)",
                mission_code,
                lowest.get("technique_id", "unknown"),
            )
            result = dict(parsed)
            result["options"] = [lowest]
            result["recommended_technique_id"] = lowest.get("technique_id")
            result["confidence"] = lowest.get("confidence", result.get("confidence", 0.0))
            return result

        result = dict(parsed)
        result["options"] = filtered
        # Update recommended_technique_id to the first remaining option
        if filtered and result.get("recommended_technique_id") not in [
            o["technique_id"] for o in filtered
        ]:
            result["recommended_technique_id"] = filtered[0]["technique_id"]
            result["confidence"] = filtered[0].get("confidence", result.get("confidence", 0.0))
        return result

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
                f"({r['technique_id']}) -> {r['target_label']} [{r['engine']}]"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_ooda_history(rows) -> str:
        if not rows:
            return "First iteration -- no prior cycles."
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
            trait = r["trait"]
            cat = r["category"].upper()

            # SPEC-043: Show PoC records in separate category for feedback loop
            if trait.startswith("poc."):
                by_cat.setdefault("PROOF_OF_CONCEPT", []).append(
                    f"  - {trait}: {r['value']}"
                )
                continue

            # SPEC-037: Exclude invalidated credentials from prompt
            if ".invalidated" in trait:
                continue

            # SPEC-028: Distinguish validated/rejected/uncertain CVEs
            if trait == "vuln.cve.rejected":
                # Exclude rejected CVEs from the prompt entirely
                continue
            elif trait == "vuln.cve.validated":
                by_cat.setdefault(cat, []).append(
                    f"  - [CONFIRMED] {r['value']}"
                )
            elif trait == "vuln.cve.uncertain":
                by_cat.setdefault(cat, []).append(
                    f"  - [UNCONFIRMED] {r['value']}"
                )
            elif trait == "vuln.cve":
                # Legacy unvalidated CVE facts
                by_cat.setdefault(cat, []).append(
                    f"  - [UNVALIDATED] {r['value']}"
                )
            else:
                by_cat.setdefault(cat, []).append(f"  - {trait}: {r['value']}")

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
    # Build prompt -- returns (system_prompt, user_prompt) tuple
    # ------------------------------------------------------------------

    async def _build_prompt(
        self, db: asyncpg.Connection, operation_id: str, observe_summary: str,
        *, attack_graph_summary: str = "",
    ) -> tuple[str, str]:
        # --- Existing queries (preserved) ---

        # Q1: Operation details
        op = await db.fetchrow(
            "SELECT * FROM operations WHERE id = $1", operation_id,
        )

        # Q2: Completed techniques
        completed = await db.fetch(
            "SELECT te.technique_id, te.status, te.result_summary "
            "FROM technique_executions te WHERE te.operation_id = $1 AND te.status = 'success'",
            operation_id,
        )
        completed_str = "\n".join(
            f"- {r['technique_id']}: {r['result_summary'] or 'completed'}" for r in completed
        ) or "None yet"

        # Q3: Failed techniques — SPEC-053 structured failure context
        #
        # JOIN targets so the LLM can see WHICH host a technique failed on
        # (not just the technique ID). Include failure_category so Rule #2
        # dead-branch pruning and Rule #9 IA-exhausted pivot can fire without
        # the LLM having to parse raw error strings.
        failed = await db.fetch(
            "SELECT te.technique_id, te.failure_category, te.error_message, "
            "te.target_id, t.hostname, t.ip_address "
            "FROM technique_executions te "
            "LEFT JOIN targets t ON t.id = te.target_id "
            "WHERE te.operation_id = $1 AND te.status = 'failed' "
            "ORDER BY te.started_at DESC NULLS LAST LIMIT 20",
            operation_id,
        )
        failed_str = "\n".join(
            f"- {r['technique_id']} on "
            f"{r['hostname'] or r['ip_address'] or 'unknown'} "
            f"[{r['failure_category'] or 'unknown'}]: "
            f"{(r['error_message'] or 'failed')[:200]}"
            for r in failed
        ) or "None"

        # Q4: Targets (enriched with os, network_segment, access_status -- SPEC-037)
        targets = await db.fetch(
            "SELECT hostname, ip_address, os, role, network_segment, "
            "is_compromised, privilege_level, access_status "
            "FROM targets WHERE operation_id = $1", operation_id,
        )
        target_lines = []
        for r in targets:
            access_status = r['access_status'] or 'unknown'
            if access_status == 'lost':
                status_str = f"ACCESS_LOST (was: {r['privilege_level'] or 'User'})"
            elif r['is_compromised']:
                status_str = f"COMPROMISED(ACTIVE) {r['privilege_level'] or ''}"
            else:
                status_str = "SECURE"
            line = (
                f"- {r['hostname']} ({r['ip_address']}) [{r['role']}] "
                f"OS={r['os'] or 'unknown'} Net={r['network_segment'] or 'unknown'} "
                f"{status_str}"
            )
            if access_status == 'lost':
                line += (
                    "\n  WARNING: Access lost -- credential invalidated. "
                    "Prioritize re-entry via alternative services."
                )
            target_lines.append(line)
        targets_str = "\n".join(target_lines) or "No targets"

        # Q5: Agents
        agents = await db.fetch(
            "SELECT paw, status, privilege, platform FROM agents WHERE operation_id = $1",
            operation_id,
        )
        agents_str = "\n".join(
            f"- {r['paw']} [{r['status']}] {r['privilege']} ({r['platform']})"
            for r in agents
        ) or "No agents"

        # --- New queries (Pattern 1, 4, 5) ---

        # Q6: Mission task tree (Pattern 1 -- PTT)
        mission_steps = await db.fetch(
            "SELECT step_number, technique_name, status, technique_id, engine, target_label "
            "FROM mission_steps WHERE operation_id = $1 ORDER BY step_number ASC",
            operation_id,
        )
        task_tree_str = self._format_task_tree(mission_steps)

        # Q7: OODA history -- compressed working memory (Pattern 5)
        ooda_history = await db.fetch(
            "SELECT iteration_number, observe_summary, act_summary, completed_at "
            "FROM ooda_iterations WHERE operation_id = $1 "
            "ORDER BY iteration_number DESC LIMIT 3",
            operation_id,
        )
        ooda_history_str = self._format_ooda_history(ooda_history)

        # Q8: Previous assessments -- episodic memory (Pattern 5)
        prev_assessments = await db.fetch(
            "SELECT situation_assessment, recommended_technique_id, reasoning_text "
            "FROM recommendations WHERE operation_id = $1 "
            "ORDER BY created_at DESC LIMIT 2",
            operation_id,
        )
        prev_assessments_str = self._format_previous_assessments(prev_assessments)

        # Q9: Kill chain tactic progression (Pattern 4)
        tactic_rows = await db.fetch(
            "SELECT DISTINCT t.tactic, t.tactic_id "
            "FROM technique_executions te JOIN techniques t ON te.technique_id = t.mitre_id "
            "WHERE te.operation_id = $1 AND te.status = 'success'",
            operation_id,
        )
        executed_tactic_ids = [r["tactic_id"] for r in tactic_rows]
        executed_tactics_str = ", ".join(
            f"{r['tactic']} ({r['tactic_id']})" for r in tactic_rows
        ) or "None yet"
        current_stage, next_stage = self._infer_kill_chain_stage(executed_tactic_ids)

        # Q10: Categorized facts (Pattern 2 -- reflection)
        facts = await db.fetch(
            "SELECT category, trait, value FROM facts "
            "WHERE operation_id = $1 ORDER BY category, collected_at DESC LIMIT 30",
            operation_id,
        )
        categorized_facts_str = self._format_categorized_facts(facts)

        # Q11: Harvested credentials for chaining context
        cred_rows = await db.fetch(
            "SELECT trait, value FROM facts "
            "WHERE operation_id = $1 AND category = 'credential' "
            "ORDER BY collected_at DESC LIMIT 10",
            operation_id,
        )
        harvested_creds_str = (
            "\n".join(f"- {r['trait']}: {r['value'][:60]}" for r in cred_rows)
            if cred_rows
            else "None harvested yet."
        )

        # Q12: Available technique playbooks (ADR-018 Layer C)
        # Use active target for primary platform detection if set
        prim_tgt_row = await db.fetchrow(
            "SELECT id, os FROM targets WHERE operation_id = $1 AND is_active = TRUE LIMIT 1",
            operation_id,
        )
        if not prim_tgt_row:
            prim_tgt_row = await db.fetchrow(
                "SELECT id, os FROM targets WHERE operation_id = $1 ORDER BY id LIMIT 1",
                operation_id,
            )
        target_os = (prim_tgt_row["os"] or "").lower() if prim_tgt_row else ""
        platform = "windows" if "windows" in target_os else "linux"
        primary_target_id = prim_tgt_row["id"] if prim_tgt_row else None

        playbook_rows = await db.fetch(
            "SELECT mitre_id, tags FROM technique_playbooks "
            "WHERE platform = $1 ORDER BY mitre_id",
            platform,
        )
        if playbook_rows:
            lines = []
            for row in playbook_rows:
                tags = json.loads(row["tags"] or "[]")
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                lines.append(f"- {row['mitre_id']}{tag_str} -- available via DirectSSHEngine")
            playbook_summary = "\n".join(lines)
        else:
            playbook_summary = "(no playbooks registered)"

        # Section 7.7 -- Lateral movement opportunities
        cred_rows = await db.fetch(
            "SELECT DISTINCT f.value, f.source_target_id, t.hostname, t.ip_address "
            "FROM facts f "
            "LEFT JOIN targets t ON t.id = f.source_target_id "
            "WHERE f.operation_id = $1 AND f.trait IN ('credential.ssh', 'credential.rdp', 'credential.winrm') "
            "LIMIT 10",
            operation_id,
        )

        uncompromised_rows = await db.fetch(
            "SELECT id, hostname, ip_address, role, os "
            "FROM targets "
            "WHERE operation_id = $1 AND (is_compromised = FALSE OR is_compromised IS NULL) "
            "LIMIT 50",
            operation_id,
        )

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
                "Available credentials:\n" + "\n".join(cred_lines) +
                "\n\nUncompromised targets:\n" + "\n".join(target_lines) +
                "\n\nConsider lateral movement via available protocols: "
                "T1021.004 (SSH), T1021.001 (WinRM/RDP)."
            )
        else:
            lateral_str = "No lateral movement opportunities identified yet."

        # Query persistence facts for the primary target of this operation
        # (primary_target_id already resolved above alongside platform detection)
        if primary_target_id:
            persist_rows = await db.fetch(
                "SELECT DISTINCT value FROM facts "
                "WHERE operation_id = $1 AND source_target_id = $2 AND trait = 'host.persistence'",
                operation_id, primary_target_id,
            )
        else:
            persist_rows = []

        if persist_rows:
            persist_info = "Persistence vectors confirmed: " + ", ".join(
                r["value"] for r in persist_rows
            )
        else:
            persist_info = "No persistence established yet."
        lateral_str = lateral_str + f"\n\nPersistence status: {persist_info}"

        # Q13: MCP tool inventory
        mcp_tools_summary = "(MCP disabled)"
        if settings.MCP_ENABLED:
            try:
                from app.services.mcp_client_manager import get_mcp_manager

                mcp_mgr = get_mcp_manager()
                if mcp_mgr:
                    mcp_tools = mcp_mgr.list_all_tools()
                    if mcp_tools:
                        mcp_tools_summary = "\n".join(
                            f"- {t.server_name}:{t.tool_name} -- {t.description}"
                            for t in mcp_tools
                        )
                    else:
                        mcp_tools_summary = "(no MCP tools connected)"
                else:
                    mcp_tools_summary = "(MCP manager not initialized)"
            except Exception:
                mcp_tools_summary = "(MCP unavailable)"

        # SPEC-048: Query OPSEC status for prompt injection
        opsec_detection_risk = 0
        opsec_noise_budget_remaining = 999
        opsec_exposure_count = 0
        try:
            from app.services.opsec_monitor import compute_status
            opsec_st = await compute_status(db, operation_id)
            opsec_detection_risk = round(opsec_st.detection_risk)
            opsec_noise_budget_remaining = opsec_st.noise_budget_remaining
            opsec_exposure_count = opsec_st.exposure_count
        except Exception:
            pass  # graceful degradation

        # SPEC-044: Query known vulnerabilities for Orient context
        vuln_rows = await db.fetch(
            "SELECT cve_id, severity, target_id, status FROM vulnerabilities "
            "WHERE operation_id = $1 AND status IN ('confirmed', 'discovered') "
            "ORDER BY severity DESC LIMIT 10",
            operation_id,
        )
        if vuln_rows:
            vuln_lines = [
                f"  - {r['cve_id']} ({r['severity']}) on target {r['target_id']} [{r['status']}]"
                for r in vuln_rows
            ]
            known_vulnerabilities_str = "\n".join(vuln_lines)
        else:
            known_vulnerabilities_str = "No confirmed vulnerabilities yet."

        # --- Assemble user prompt ---
        mission_code = (op["mission_profile"] if op else None) or "SP"
        mission_prof = get_profile(mission_code)
        user_prompt = _ORIENT_USER_PROMPT_TEMPLATE.format(
            codename=op["codename"] if op else "Unknown",
            strategic_intent=op["strategic_intent"] if op else "Unknown",
            status=op["status"] if op else "unknown",
            mission_profile=mission_code,
            mission_profile_name=mission_prof.get("name", mission_code),
            max_noise=mission_prof.get("max_noise", "high"),
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
            mcp_tools_summary=mcp_tools_summary,
            relay_infrastructure=_format_relay_infrastructure(),
            attack_graph_summary=attack_graph_summary or "Not available.",
            known_vulnerabilities=known_vulnerabilities_str,
            opsec_detection_risk=opsec_detection_risk,
            opsec_noise_budget_remaining=opsec_noise_budget_remaining,
            opsec_exposure_count=opsec_exposure_count,
        )

        # --- Section 8.5: Security Skills injection (SPEC-043 A3) ---
        from app.services.skill_loader import load_skills

        last_rec_technique = None
        if prev_assessments:
            last_rec_technique = prev_assessments[0]["recommended_technique_id"]

        skill_tactic_id = None
        if last_rec_technique:
            tac_row = await db.fetchrow(
                "SELECT tactic_id FROM techniques WHERE mitre_id = $1 LIMIT 1",
                last_rec_technique,
            )
            skill_tactic_id = tac_row["tactic_id"] if tac_row else None

        skills_section = load_skills(
            last_rec_technique or "", skill_tactic_id
        )
        if skills_section:
            user_prompt += f"\n\n{skills_section}"

        # --- Section 9: Operator directive (if any) ---
        directive_row = await db.fetchrow(
            "SELECT id, directive FROM ooda_directives "
            "WHERE operation_id = $1 AND consumed_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1",
            operation_id,
        )
        if directive_row:
            user_prompt += (
                f"\n\n## OPERATOR DIRECTIVE (PRIORITY)\n{directive_row['directive']}"
            )
            await db.execute(
                "UPDATE ooda_directives SET consumed_at = NOW() WHERE id = $1",
                directive_row["id"],
            )

        # Dynamically include/exclude MCP Engine sections based on availability
        _mcp_available = mcp_tools_summary not in (
            "(MCP disabled)",
            "(MCP unavailable)",
            "(MCP manager not initialized)",
            "(no MCP tools connected)",
        )
        if _mcp_available:
            _mcp_engine_section = (
                '- MCP Engine ("mcp"): stateless recon/OSINT/vuln-lookup tools '
                "via MCP protocol. Prefer for reconnaissance, OSINT, and "
                "vulnerability scanning when MCP tools are listed in Section 7.8.\n"
            )
            _mcp_or_note = " or MCP"
            _mcp_engine_guide = (
                '- "mcp": Run MCP reconnaissance/enumeration tools '
                "(nmap, vuln-lookup, credential-checker)"
            )
        else:
            _mcp_engine_section = ""
            _mcp_or_note = ""
            _mcp_engine_guide = ""

        system_prompt = _ORIENT_SYSTEM_PROMPT.format(
            mcp_engine_section=_mcp_engine_section,
            mcp_or_note=_mcp_or_note,
            mcp_engine_guide=_mcp_engine_guide,
        )

        return system_prompt, user_prompt

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """LLM API call via shared LLMClient (API Key / OAuth / OpenAI / mock)."""
        from app.services.llm_client import get_llm_client

        result = await get_llm_client().call(system_prompt, user_prompt, task_type="orient_analysis")
        if not result:
            if settings.MOCK_LLM:
                logger.info("No LLM backend available, using mock recommendation")
                return json.dumps(_MOCK_RECOMMENDATION)
            logger.error("No LLM backend available and MOCK_LLM=False — orient phase will abort")
            return ""
        return result

    async def _store_recommendation(
        self, db: asyncpg.Connection, operation_id: str, parsed: dict
    ) -> dict:
        """Store recommendation in DB and return as dict."""
        rec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Get current OODA iteration
        row = await db.fetchrow(
            "SELECT id FROM ooda_iterations WHERE operation_id = $1 "
            "ORDER BY iteration_number DESC LIMIT 1",
            operation_id,
        )
        ooda_iter_id = row["id"] if row else None

        options_json = json.dumps(parsed.get("options", []))
        await db.execute(
            "INSERT INTO recommendations "
            "(id, operation_id, ooda_iteration_id, situation_assessment, "
            "recommended_technique_id, confidence, options, reasoning_text, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            rec_id, operation_id, ooda_iter_id,
            parsed.get("situation_assessment", ""),
            parsed.get("recommended_technique_id", ""),
            parsed.get("confidence", 0.0),
            options_json,
            parsed.get("reasoning_text", ""),
            now,
        )

        # Link recommendation to OODA iteration
        if ooda_iter_id:
            await db.execute(
                "UPDATE ooda_iterations SET recommendation_id = $1 WHERE id = $2",
                rec_id, ooda_iter_id,
            )

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
