# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Per-node AI tactical intelligence summary.

Generates structured Chinese summaries for individual target hosts,
compressing 30-90 seconds of analyst cognitive work into a 3-second read.
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone

import asyncpg

from app.config import settings, get_task_model_map
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

_NODE_SUMMARY_SYSTEM_PROMPT = """\
你是 Athena C5ISR 的單節點情報分析官。
你的職責是對單一目標主機的收集情報進行戰術分析，產出結構化的繁體中文摘要。

## 分析框架

### 1. 攻擊面分析（Attack Surface）
盤點目標暴露的服務、版本、已知弱點。標注可利用的攻擊向量。

### 2. 憑證鏈分析（Credential Chain）
列出所有已收集的憑證（SSH、RDP、WinRM、hash）。
評估可授予的存取等級與憑證重用（credential reuse）的橫向移動潛力。

### 3. 橫向移動向量（Lateral Movement）
根據已取得的憑證和目標網路拓撲，評估可橫向移動的路徑。

### 4. 持久化機會（Persistence）
評估可建立持久化存取的機制（cron、systemd、SSH key、scheduled task）。

### 5. 風險評估（Risk Assessment）
以 低/中/高/嚴重 評估此節點的偵測風險。

### 6. 建議下一步（Recommended Next）
根據 MITRE ATT&CK 殺傷鏈，建議對此節點的下一個戰術動作。
引用具體的 TXXXX 技術編號。

## 輸出格式
回應合法 JSON，格式：
{
  "attack_surface": "30-80字分析",
  "credential_chain": "30-80字分析",
  "lateral_movement": "30-80字分析",
  "persistence": "30-80字分析",
  "risk_assessment": "風險等級 + 說明",
  "recommended_next": "TXXXX + 理由"
}

只回傳 JSON，不要加 markdown 標記或其他文字。"""

_MOCK_SUMMARY = {
    "attack_surface": "目標主機執行 Linux 系統，開放 SSH (22/tcp) 及 Samba (139/tcp) 服務。SSH 版本 OpenSSH 4.7p1 存在已知弱點 CVE-2008-XXXX。",
    "credential_chain": "已取得兩組 SSH 憑證：msfadmin（管理員）及 user（一般使用者）。msfadmin 帳戶可直接 SSH 登入取得 shell。",
    "lateral_movement": "透過 msfadmin 憑證可嘗試對同網段 192.168.0.0/24 其他主機進行 SSH credential reuse。",
    "persistence": "Cron 目錄可寫入，可建立排程反向 shell。/etc/passwd 顯示 root 帳戶存在，提權後可植入 SSH authorized_keys。",
    "risk_assessment": "中風險 — 已取得有效憑證但權限尚未提升至 root。目標未發現 EDR 或日誌轉發。",
    "recommended_next": "建議執行 T1548.001 (Setuid/Setgid) 嘗試本地提權，或 T1021.004 (SSH) 橫向移動至鄰近主機。",
}

_NO_FACTS_SUMMARY = {
    "attack_surface": "尚無情報 — 請先執行偵察掃描。",
    "credential_chain": "尚無憑證資料。",
    "lateral_movement": "無法評估 — 缺乏情報。",
    "persistence": "無法評估 — 缺乏情報。",
    "risk_assessment": "無法評估。",
    "recommended_next": "建議執行 T1046 (Network Service Discovery) 或 T1595.001 (主動掃描) 收集基礎情報。",
}

_SUMMARY_FIELDS = [
    "attack_surface",
    "credential_chain",
    "lateral_movement",
    "persistence",
    "risk_assessment",
    "recommended_next",
]

# Category display order and per-category limits
_CATEGORY_ORDER = ["credential", "host", "service", "network"]
_PER_CATEGORY_LIMIT = 15
_TOTAL_FACTS_LIMIT = 50

# Cache: (operation_id, target_id, facts_hash) → (summary_dict, generated_at, model)
_CACHE_MAX = 200


class _SummaryCache:
    def __init__(self, max_size: int = _CACHE_MAX):
        self._data: OrderedDict[str, tuple[dict, str, str]] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> tuple[dict, str, str] | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, summary: dict, generated_at: str, model: str) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (summary, generated_at, model)
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)


_cache = _SummaryCache()

# Rate limit: track last call time per (op, target)
_last_call: dict[str, float] = {}
_COOLDOWN_SEC = 5.0


def _compute_facts_hash(facts: list[dict]) -> str:
    """SHA-256 of sorted trait+value pairs, truncated to 16 chars."""
    pairs = sorted(f"{f['trait']}={f['value']}" for f in facts)
    return hashlib.sha256("|".join(pairs).encode()).hexdigest()[:16]


def _build_user_prompt(target: dict, facts: list[dict]) -> str:
    """Build the user prompt with target info and grouped facts."""
    is_compromised = "是" if target.get("is_compromised") else "否"
    prompt = f"""## 目標主機資訊
- 主機名稱：{target.get('hostname', '—')}
- IP 位址：{target.get('ip_address', '—')}
- 作業系統：{target.get('os') or '—'}
- 角色：{target.get('role') or '—'}
- 已滲透：{is_compromised}
- 權限等級：{target.get('privilege_level') or '—'}
- 網路區段：{target.get('network_segment') or '—'}

## 收集情報（{len(facts)} 項）
"""
    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for f in facts:
        cat = f.get("category", "other")
        by_cat.setdefault(cat, []).append(f)

    for cat in _CATEGORY_ORDER:
        cat_facts = by_cat.pop(cat, [])
        if not cat_facts:
            continue
        prompt += f"\n### {cat.upper()}\n"
        for f in cat_facts[:_PER_CATEGORY_LIMIT]:
            prompt += f"  - {f['trait']}: {f['value']}\n"

    # Any remaining categories
    for cat, cat_facts in sorted(by_cat.items()):
        prompt += f"\n### {cat.upper()}\n"
        for f in cat_facts[:_PER_CATEGORY_LIMIT]:
            prompt += f"  - {f['trait']}: {f['value']}\n"

    return prompt


def _parse_summary(raw: str) -> dict:
    """Parse LLM response into summary dict. Fallback: raw text in attack_surface."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        # Remove first line (```json) and last line (```)
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        parsed = json.loads(text)
        # Ensure all fields exist
        result = {}
        for field in _SUMMARY_FIELDS:
            result[field] = str(parsed.get(field, "—"))
        return result
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Failed to parse LLM summary as JSON, using raw text")
        result = {field: "—" for field in _SUMMARY_FIELDS}
        result["attack_surface"] = text[:500] if text else "—"
        return result


async def get_node_summary(
    db: asyncpg.Connection,
    operation_id: str,
    target_id: str,
    force_refresh: bool = False,
) -> dict:
    """Generate or retrieve cached AI summary for a target node.

    Returns dict with keys: summary, fact_count, cached, generated_at, model
    """
    # Verify target exists
    target_row = await db.fetchrow(
        "SELECT * FROM targets WHERE id = $1 AND operation_id = $2",
        target_id, operation_id,
    )
    if not target_row:
        return None

    target = dict(target_row)

    # Fetch facts for this target (server-side filter)
    fact_rows = await db.fetch(
        "SELECT trait, value, category FROM facts "
        "WHERE operation_id = $1 AND source_target_id = $2 "
        "ORDER BY collected_at DESC LIMIT $3",
        operation_id, target_id, _TOTAL_FACTS_LIMIT,
    )
    facts = [dict(r) for r in fact_rows]

    # 0 facts → static response, no LLM call
    if not facts:
        return {
            "summary": _NO_FACTS_SUMMARY,
            "fact_count": 0,
            "cached": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": "none",
        }

    facts_hash = _compute_facts_hash(facts)
    cache_key = f"{operation_id}:{target_id}:{facts_hash}"

    # Check cache
    if not force_refresh:
        cached = _cache.get(cache_key)
        if cached:
            summary, generated_at, model = cached
            return {
                "summary": summary,
                "fact_count": len(facts),
                "cached": True,
                "generated_at": generated_at,
                "model": model,
            }

    # Rate limit check
    rate_key = f"{operation_id}:{target_id}"
    now = time.time()
    last = _last_call.get(rate_key, 0)
    if now - last < _COOLDOWN_SEC and not force_refresh:
        # Return cached if available, else wait
        cached = _cache.get(cache_key)
        if cached:
            summary, generated_at, model = cached
            return {
                "summary": summary,
                "fact_count": len(facts),
                "cached": True,
                "generated_at": generated_at,
                "model": model,
            }
    _last_call[rate_key] = now

    # Mock mode
    model_name = get_task_model_map().get("node_summary", settings.CLAUDE_MODEL)
    if settings.MOCK_LLM:
        generated_at = datetime.now(timezone.utc).isoformat()
        _cache.put(cache_key, _MOCK_SUMMARY, generated_at, "mock")
        return {
            "summary": _MOCK_SUMMARY,
            "fact_count": len(facts),
            "cached": False,
            "generated_at": generated_at,
            "model": "mock",
        }

    # Call LLM
    user_prompt = _build_user_prompt(target, facts)
    try:
        raw = await get_llm_client().call(
            _NODE_SUMMARY_SYSTEM_PROMPT,
            user_prompt,
            task_type="node_summary",
            max_tokens=2000,
            temperature=0.5,
            timeout=30.0,
        )
    except Exception as e:
        logger.error("Node summary LLM call failed: %s", e)
        raise

    if not raw:
        raise RuntimeError("LLM returned empty response")

    summary = _parse_summary(raw)
    generated_at = datetime.now(timezone.utc).isoformat()
    _cache.put(cache_key, summary, generated_at, model_name)

    return {
        "summary": summary,
        "fact_count": len(facts),
        "cached": False,
        "generated_at": generated_at,
        "model": model_name,
    }
