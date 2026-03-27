# SPEC-043：Security Skills Library & PoC Auto Generation

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-043 |
| **關聯 ADR** | 無（獨立功能，借鑑 CyberStrikeAI A3 + Strix B1 概念） |
| **估算複雜度** | 中 |

---

## 🎯 目標（Goal）

> 為 Orient 階段注入結構化的攻擊知識（Security Skills Library），使 LLM 在推薦技術時具備更深層的攻擊方法論與繞過技巧；同時在 Act 階段成功執行技術後，自動記錄可重現的 PoC（Proof of Concept）步驟，供報告產出與後續驗證使用。

**A3 Security Skills Library** — 解決 Orient LLM 對特定攻擊技術的知識不足問題，提供 MITRE 技術對應的攻擊方法論、工具用法、繞過技巧。

**B1 PoC Auto Generation** — 解決滲透測試報告中「重現步驟」需手動整理的痛點，自動將成功執行的技術記錄為結構化 PoC，對紅隊操作員與報告產出有直接價值。

---

## 📥 輸入規格（Inputs）

### A3 — Skills Library

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| technique_id | string | Orient 推薦結果 | MITRE ATT&CK ID 格式（`TXXXX` 或 `TXXXX.XXX`） |
| tactic_id | string | techniques 表 | MITRE Tactic ID（`TA00XX`） |

**Skill 檔案格式（Markdown）：**

每個 skill 檔案存放於 `backend/app/data/skills/`，格式如下：

```markdown
---
title: SQL Injection
category: web_application
applicable_techniques:
  - T1190      # Exploit Public-Facing Application
  - T1059.007  # Command and Scripting Interpreter: JavaScript
mitre_tactics:
  - TA0001     # Initial Access
  - TA0002     # Execution
max_token_estimate: 800
---

## Attack Methodology

1. **Discovery**: Identify injection points via parameter fuzzing...
2. **Exploitation**: Use UNION-based, blind boolean, or time-based techniques...
3. **Post-Exploitation**: Extract database schema, dump credentials...

## Bypass Techniques

- WAF bypass: inline comments (`/*!50000 UNION*/`), case alternation
- Prepared statement detection: use stacked queries where supported
- Character encoding: UTF-8 overlong encoding, hex encoding

## Tool Usage Tips

- sqlmap: `sqlmap -u "URL" --batch --level=5 --risk=3`
- Manual: `' OR 1=1--`, `' UNION SELECT NULL,NULL--`
```

**初始 Skill 檔案清單：**

| 檔案名稱 | 類別 | 對應 Tactics |
|----------|------|-------------|
| `sql_injection.md` | web_application | TA0001, TA0002 |
| `xss.md` | web_application | TA0001, TA0002 |
| `privilege_escalation_linux.md` | post_exploitation | TA0004 |
| `privilege_escalation_windows.md` | post_exploitation | TA0004 |
| `lateral_movement.md` | network | TA0008 |
| `credential_dumping.md` | credential_access | TA0006 |
| `web_scanning.md` | reconnaissance | TA0043 |
| `network_recon.md` | reconnaissance | TA0043 |

### B1 — PoC Auto Generation

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| technique_id | string | technique_executions | 已成功執行的技術 ID |
| target_id | string (UUID) | technique_executions | 執行對象 |
| operation_id | string (UUID) | operations | 當前作戰 ID |
| result | ExecutionResult | engine_router | `result.success == True` 時觸發 |

---

## 📤 輸出規格（Expected Output）

### A3 — Orient Prompt 注入格式

在 `_ORIENT_USER_PROMPT_TEMPLATE` 中新增 Section 9（現有 Section 9 為 Operator Directive，動態附加；Skills 使用 Section 8.5）：

```
## 8.5. 📚 RELEVANT SECURITY KNOWLEDGE

### SQL Injection (applicable to T1190)
**Attack Methodology:**
1. Discovery: Identify injection points via parameter fuzzing...
2. Exploitation: Use UNION-based, blind boolean, or time-based techniques...

**Bypass Techniques:**
- WAF bypass: inline comments, case alternation...

**Tool Usage Tips:**
- sqlmap: `sqlmap -u "URL" --batch --level=5 --risk=3`

---
### Credential Dumping (applicable to T1003.001)
...
```

**限制：** 每次 Orient 呼叫最多載入 2 個 skill 檔案（token budget 控制）。

**Skill 匹配邏輯：**

```python
# backend/app/services/skill_loader.py

_SKILL_TECHNIQUE_MAP: dict[str, list[str]] = {
    # technique_id → skill file names (without .md)
    "T1190": ["sql_injection", "xss"],
    "T1059.007": ["sql_injection", "xss"],
    "T1003": ["credential_dumping"],
    "T1003.001": ["credential_dumping"],
    "T1003.002": ["credential_dumping"],
    "T1003.003": ["credential_dumping"],
    "T1068": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548.001": ["privilege_escalation_linux"],
    "T1548.002": ["privilege_escalation_windows"],
    "T1021": ["lateral_movement"],
    "T1021.001": ["lateral_movement"],
    "T1021.004": ["lateral_movement"],
    "T1595": ["network_recon", "web_scanning"],
    "T1046": ["network_recon"],
}

_TACTIC_SKILL_FALLBACK: dict[str, list[str]] = {
    # tactic_id → fallback skill files when technique not in map
    "TA0001": ["sql_injection", "xss"],
    "TA0004": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "TA0006": ["credential_dumping"],
    "TA0008": ["lateral_movement"],
    "TA0043": ["network_recon", "web_scanning"],
}
```

**匹配優先順序：**
1. `technique_id` 精確匹配 → `_SKILL_TECHNIQUE_MAP[technique_id]`
2. `technique_id` 父級匹配（`T1003.001` → 嘗試 `T1003`）
3. `tactic_id` fallback → `_TACTIC_SKILL_FALLBACK[tactic_id]`
4. 無匹配 → 不注入 skill section

### B1 — PoCRecord 資料結構

```python
# backend/app/models/poc_record.py

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json


@dataclass
class PoCRecord:
    """結構化 PoC 記錄，用於自動產出可重現的攻擊步驟。"""

    technique_id: str                    # MITRE ATT&CK ID
    target_ip: str                       # 目標 IP
    commands_executed: list[str]         # 實際執行的指令列表
    input_params: dict                   # 輸入參數（credential, protocol, etc.）
    output_snippet: str                  # 執行輸出摘要（截取前 1000 字元）
    environment: dict                    # OS, services, privilege_level
    timestamp: str = field(              # ISO 8601
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reproducible: bool = True            # 是否可重現

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "PoCRecord":
        return cls(**json.loads(raw))
```

**儲存方式：** 使用現有 `facts` 表，不新增 DB schema。

| 欄位 | 值 |
|------|---|
| trait | `poc.{technique_id}` |
| value | `PoCRecord.to_json()` （JSON 字串） |
| category | `poc` |
| source_technique_id | technique_id |
| source_target_id | target_id |
| operation_id | operation_id |
| score | 1 |

**PoC 報告 API：**

```
GET /api/operations/{operation_id}/poc
```

**成功回應（200）：**

```json
{
  "operation_id": "uuid",
  "poc_records": [
    {
      "technique_id": "T1003.001",
      "target_ip": "192.168.0.23",
      "commands_executed": [
        "procdump64.exe -accepteula -ma lsass.exe lsass.dmp",
        "mimikatz.exe \"sekurlsa::minidump lsass.dmp\" \"sekurlsa::logonPasswords\""
      ],
      "input_params": {
        "credential": "admin:P@ssw0rd",
        "protocol": "ssh"
      },
      "output_snippet": "Authentication Id : 0 ; 999\nNTLM : aad3b435...",
      "environment": {
        "os": "Windows Server 2019",
        "services": ["LSASS", "RDP"],
        "privilege_level": "SYSTEM"
      },
      "timestamp": "2026-03-08T10:30:00Z",
      "reproducible": true
    }
  ],
  "total": 1
}
```

**失敗回應：**

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| Operation 不存在 | 404 | `{"detail": "Operation not found"}` |
| 無 PoC 記錄 | 200 | `{"operation_id": "uuid", "poc_records": [], "total": 0}` |

---

## 副作用與連動（Side Effects）

| 副作用 | 觸發條件 | 影響模組 | 驗證方式 |
|--------|----------|----------|----------|
| Skill 內容注入 Orient prompt（+400-800 tokens/skill） | Orient `_build_prompt()` 執行時 | `backend/app/services/orient_engine.py` | 單元測試驗證 prompt 含 `## 8.5. RELEVANT SECURITY KNOWLEDGE` |
| `poc.*` fact 插入 facts 表 | `_finalize_execution` 成功路徑 / `_execute_metasploit` 成功路徑 | `backend/app/services/engine_router.py` | 單元測試驗證 DB 中 `poc.*` fact 存在 |
| Orient `_format_categorized_facts` 排除 `poc.*` trait | Orient prompt 組裝時 | `backend/app/services/orient_engine.py` | 單元測試驗證 categorized_facts 不含 `poc.*` |
| Attack Graph 忽略 `poc.*` trait | 攻擊圖 rebuild 時 | `backend/app/services/attack_graph_engine.py` | 單元測試驗證 `poc.*` 不產生攻擊圖節點 |
| FactCategory enum 新增 `POC = "poc"` | 系統初始化時 | `backend/app/models/enums.py` | import 驗證 `FactCategory.POC` 存在 |
| 新增 `/api/operations/{id}/poc` API | HTTP GET 請求 | `backend/app/routers/poc.py` | API 測試驗證回傳結構正確 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：Skill 檔案不存在或格式錯誤 — `SkillLoader` 回傳空字串，Orient 照常運作無 skill section
- **Case 2**：同一 technique 對應多個 skill（如 `T1190` → `sql_injection` + `xss`）— 只取前 2 個（已受 max 2 限制），按 `_SKILL_TECHNIQUE_MAP` 列表順序
- **Case 3**：PoC 產出時 `result.output` 為空 — `output_snippet` 設為空字串，`reproducible` 設為 `False`
- **Case 4**：同一 technique 對同一 target 執行多次成功 — 每次都產出獨立的 PoC fact（`INSERT OR IGNORE` 防重複 trait+value 組合）
- **Case 5**：Metasploit 成功路徑的 PoC 記錄 — `_execute_metasploit` 成功後同樣記錄 PoC，`commands_executed` 為 exploit module 路徑
- **Case 6**：`commands_executed` 資訊不可得（如 mock engine）— 設為 `["(mock execution)"]`，`reproducible` 設為 `False`
- **Case 7**：Skill 檔案超過 token budget — 截取前 800 tokens（以字元估算：約 3200 字元）

## Rollback Plan

| 回滾步驟 | 資料影響 | 回滾驗證 | 回滾已測試 |
|----------|----------|----------|-----------|
| `git revert <commit>` | Skill 檔案為靜態 Markdown，刪除即可。`poc.*` facts 保留在 DB 中不影響既有功能（trait 前綴隔離） | `make test` 全數通過；grep 確認 `skill_loader` / `poc_record` import 不存在 | 否（待實作後驗證） |
| 可選：`DELETE FROM facts WHERE trait LIKE 'poc.%'` | 清理殘留 PoC facts | 查詢 `SELECT COUNT(*) FROM facts WHERE trait LIKE 'poc.%'` 回傳 0 | 否 |

> **不可逆評估**：完全可逆。Skill 檔案為靜態 Markdown，`poc.*` facts 以 trait 前綴隔離。

---

## 測試矩陣（Test Matrix）

| ID | 類型 | 場景描述 | 輸入 | 預期結果 | 對應驗收場景 |
|----|------|----------|------|----------|-------------|
| P1 | 正向 | Skill 精確匹配 — T1190 | `load_skills("T1190")` | 回傳含 `sql_injection` 和 `xss` 的 skill 內容 | Scenario: Security skills injection into Orient prompt |
| P2 | 正向 | Skill 父級匹配 — T1003.001 | `load_skills("T1003.001")` | 回傳 `credential_dumping` 內容 | Scenario: Security skills injection into Orient prompt |
| P3 | 正向 | Skill tactic fallback — TA0008 | `load_skills("T9999", "TA0008")` | 回傳 `lateral_movement` 內容 | Scenario: Security skills injection into Orient prompt |
| P4 | 正向 | PoC 自動記錄 — _finalize_execution 成功 | `result.success=True, result.output="uid=0(root)"` | DB 中出現 `poc.{technique_id}` fact，value 為合法 JSON | Scenario: PoC auto generation on successful exploit |
| P5 | 正向 | PoC API — 正常查詢 | `GET /api/operations/{op_id}/poc` | 回傳 `{"poc_records": [...], "total": N}` | Scenario: PoC auto generation on successful exploit |
| P6 | 正向 | Metasploit PoC 記錄 | `_execute_metasploit` 成功 | DB 中出現 `poc.{technique_id}` fact，`commands_executed` 含 `metasploit:` 前綴 | Scenario: PoC auto generation on successful exploit |
| N1 | 負向 | Skill 檔案不存在 | `load_skills("T9999")` | 回傳空字串，Orient 照常運作 | Scenario: Security skills injection into Orient prompt |
| N2 | 負向 | PoC API — operation 不存在 | `GET /api/operations/invalid-id/poc` | 404 `{"detail": "Operation not found"}` | Scenario: PoC auto generation on successful exploit |
| N3 | 負向 | PoC — result.output 為空 | `result.success=True, result.output=""` | `output_snippet=""`, `reproducible=False` | Scenario: PoC auto generation on successful exploit |
| B1 | 邊界 | Skill token budget — 超過 3200 字元 | skill 檔案內容 5000 字元 | 截取前 3200 字元 | Scenario: Security skills injection into Orient prompt |
| B2 | 邊界 | 同一 technique 多次成功執行 PoC | 連續 2 次 `_finalize_execution` 成功 | `INSERT OR IGNORE` 不產生重複 fact | Scenario: PoC auto generation on successful exploit |
| B3 | 邊界 | Orient categorized_facts 排除 poc.* | facts 表含 `poc.T1190` fact | `_format_categorized_facts` 不包含 `poc.*` | Scenario: Security skills injection into Orient prompt |

---

## 驗收場景（Acceptance Scenarios）

```gherkin
Feature: Security Skills Library and PoC Auto Generation
  SPEC-043 — Skill 知識注入 Orient + 成功 exploit 自動記錄 PoC。

  Background:
    Given 系統已初始化資料庫
    And operation "op-test" 已建立
    And target "target-001" IP "192.168.0.23" 已加入 operation

  Scenario: Security skills injection into Orient prompt
    Given skill 檔案 "sql_injection.md" 存在於 backend/app/data/skills/
    When 呼叫 load_skills("T1190")
    Then 回傳字串含 "## 8.5. RELEVANT SECURITY KNOWLEDGE"
    And 回傳字串含 "SQL Injection" 內容
    When 呼叫 load_skills("T1003.001")
    Then 回傳字串含 "credential_dumping" 相關內容（父級匹配）
    When 呼叫 load_skills("T9999", "TA0008")
    Then 回傳字串含 "lateral_movement" 相關內容（tactic fallback）
    When 呼叫 load_skills("T9999")
    Then 回傳空字串
    And Orient prompt 組裝正常完成無 exception

  Scenario: PoC auto generation on successful exploit
    Given technique "T1003.001" 對 target "target-001" 執行成功
    And result.output 為 "Authentication Id : 0 ; 999\nNTLM : aad3b435..."
    When _finalize_execution 完成
    Then DB 中存在 fact trait="poc.T1003.001" category="poc"
    And fact value 為合法 JSON 且可透過 PoCRecord.from_json() 反序列化
    And PoCRecord.output_snippet 不超過 1000 字元
    When GET /api/operations/op-test/poc
    Then 回傳 HTTP 200
    And response 含 "poc_records" 陣列長度 >= 1
    And poc_records[0].technique_id 為 "T1003.001"
    When GET /api/operations/invalid-id/poc
    Then 回傳 HTTP 404
```

---

## 追溯性（Traceability）

| 項目 | 檔案路徑 | 狀態 | 備註 |
|------|----------|------|------|
| SPEC 文件 | `docs/specs/SPEC-043-security-skills-library-and-poc-auto-generation.md` | 已建立 | 本文件 |
| 後端實作 — SkillLoader | `backend/app/services/skill_loader.py` | 已存在 | Skill 載入模組 |
| 後端實作 — Orient 整合 | `backend/app/services/orient_engine.py` | 已存在 | skill section 注入 + poc fact 排除 |
| 後端實作 — PoCRecord | `backend/app/models/poc_record.py` | 已存在 | PoC dataclass |
| 後端實作 — PoC 記錄 | `backend/app/services/engine_router.py` | 已存在 | `_record_poc()` / `_execute_metasploit` PoC |
| 後端實作 — PoC API | `backend/app/routers/poc.py` | 已存在 | PoC 報告 API |
| 後端實作 — Enum | `backend/app/models/enums.py` | 已存在 | `FactCategory.POC` |
| 後端測試 — SkillLoader | `backend/tests/test_skill_loader.py` | 已存在 | skill 載入測試 |
| 後端測試 — PoC | `backend/tests/test_poc.py` | 已存在 | PoC 記錄測試 |
| 後端測試 — PoC router | `backend/tests/test_poc_router.py` | 已存在 | PoC API 路由測試 |
| Skill 檔案 | `backend/app/data/skills/*.md` | （待確認） | 8 個 Markdown skill 檔案 |
| 前端實作 | — | （待實作） | Operation Detail PoC 區塊 |
| E2E 測試 | — | N/A | 前端 PoC 顯示可延後 |

> 追溯日期：2026-03-26

---

## 可觀測性（Observability）

| 項目 | 類型 | 名稱/格式 | 觸發條件 | 說明 |
|------|------|-----------|----------|------|
| Skill 載入 | log (DEBUG) | `Skill file not found: %s` | skill 檔案不存在 | 記錄缺失的 skill 路徑 |
| Skill 讀取失敗 | log (WARNING) | `Failed to read skill file: %s` | skill 檔案讀取異常 | 含 exc_info |
| PoC 記錄成功 | log (INFO) | `PoC recorded: technique=%s target=%s` | `_record_poc()` 成功寫入 | 記錄 technique_id 和 target_id |
| PoC 重複跳過 | log (DEBUG) | `PoC fact already exists: poc.%s` | `INSERT OR IGNORE` 未插入 | 冪等執行記錄 |
| Orient prompt token 增量 | log (DEBUG) | `Skills section injected: %d chars (%d skills)` | skill section 非空 | 記錄注入字元數和 skill 數量 |
| 前端 | N/A | — | — | 前端 PoC 顯示為純渲染，無後端可觀測需求 |

---

## 實作細節

### A3 — SkillLoader 模組

**新增檔案：** `backend/app/services/skill_loader.py`

```python
"""Security Skills Library — 載入並注入攻擊知識至 Orient prompt。"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_SKILLS_DIR = Path(__file__).parent.parent / "data" / "skills"
_MAX_SKILLS_PER_CALL = 2
_MAX_CHARS_PER_SKILL = 3200  # ~800 tokens

# technique_id → skill file names
_SKILL_TECHNIQUE_MAP: dict[str, list[str]] = {
    "T1190": ["sql_injection", "xss"],
    "T1059.007": ["sql_injection", "xss"],
    "T1003": ["credential_dumping"],
    "T1003.001": ["credential_dumping"],
    "T1003.002": ["credential_dumping"],
    "T1003.003": ["credential_dumping"],
    "T1068": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548.001": ["privilege_escalation_linux"],
    "T1548.002": ["privilege_escalation_windows"],
    "T1021": ["lateral_movement"],
    "T1021.001": ["lateral_movement"],
    "T1021.004": ["lateral_movement"],
    "T1595": ["network_recon", "web_scanning"],
    "T1046": ["network_recon"],
}

_TACTIC_SKILL_FALLBACK: dict[str, list[str]] = {
    "TA0001": ["sql_injection", "xss"],
    "TA0004": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "TA0006": ["credential_dumping"],
    "TA0008": ["lateral_movement"],
    "TA0043": ["network_recon", "web_scanning"],
}


def load_skills(technique_id: str, tactic_id: str | None = None) -> str:
    """載入與 technique/tactic 相關的 skill 內容。

    回傳格式化的 Markdown 字串，適合直接注入 Orient prompt。
    最多回傳 _MAX_SKILLS_PER_CALL 個 skill。
    """
    skill_names = _resolve_skill_names(technique_id, tactic_id)
    if not skill_names:
        return ""

    sections: list[str] = []
    for name in skill_names[:_MAX_SKILLS_PER_CALL]:
        content = _read_skill_file(name)
        if content:
            sections.append(content)

    if not sections:
        return ""

    return "## 8.5. RELEVANT SECURITY KNOWLEDGE\n\n" + "\n---\n".join(sections)


def _resolve_skill_names(technique_id: str, tactic_id: str | None) -> list[str]:
    # 1. 精確匹配
    if technique_id in _SKILL_TECHNIQUE_MAP:
        return _SKILL_TECHNIQUE_MAP[technique_id]

    # 2. 父級匹配 (T1003.001 → T1003)
    parent = technique_id.split(".")[0] if "." in technique_id else None
    if parent and parent in _SKILL_TECHNIQUE_MAP:
        return _SKILL_TECHNIQUE_MAP[parent]

    # 3. Tactic fallback
    if tactic_id and tactic_id in _TACTIC_SKILL_FALLBACK:
        return _TACTIC_SKILL_FALLBACK[tactic_id]

    return []


def _read_skill_file(name: str) -> str | None:
    path = _SKILLS_DIR / f"{name}.md"
    if not path.exists():
        logger.debug("Skill file not found: %s", path)
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        # 移除 YAML front matter
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                raw = raw[end + 3:].strip()
        return raw[:_MAX_CHARS_PER_SKILL]
    except Exception:
        logger.warning("Failed to read skill file: %s", path, exc_info=True)
        return None
```

**Orient 整合點（`orient_engine.py` `_build_prompt`）：**

在組裝 `user_prompt` 之前，於現有 Q12（playbook）之後新增：

```python
# Q14: Security Skills injection
from app.services.skill_loader import load_skills

# 使用最近一次推薦的 technique_id 作為 skill 查詢依據
last_rec_technique = None
if prev_assessments:
    last_rec_technique = prev_assessments[0]["recommended_technique_id"]

# 取得該 technique 對應的 tactic_id
skill_tactic_id = None
if last_rec_technique:
    tac_cursor = await db.execute(
        "SELECT tactic_id FROM techniques WHERE mitre_id = ? LIMIT 1",
        (last_rec_technique,),
    )
    tac_row = await tac_cursor.fetchone()
    skill_tactic_id = tac_row["tactic_id"] if tac_row else None

skills_section = load_skills(
    last_rec_technique or "", skill_tactic_id
)
```

然後在 `user_prompt` 組裝後、Operator Directive 前附加：

```python
if skills_section:
    user_prompt += f"\n\n{skills_section}"
```

### B1 — PoC 記錄邏輯

**整合點（`engine_router.py` `_finalize_execution`）：**

在 `_finalize_execution` 方法的成功路徑中，`facts_count` 更新後加入：

```python
# B1: PoC Auto Generation — record reproduction steps on success
if result.success:
    await self._record_poc(
        db, technique_id, target_id, operation_id, result, engine,
    )
```

**新增方法 `_record_poc`：**

```python
async def _record_poc(
    self,
    db: aiosqlite.Connection,
    technique_id: str,
    target_id: str,
    operation_id: str,
    result: ExecutionResult,
    engine: str,
) -> None:
    """成功執行後自動記錄 PoC 重現步驟。"""
    from app.models.poc_record import PoCRecord

    target_ip = await self._get_target_ip(db, target_id) or target_id

    # 推斷環境資訊
    db.row_factory = aiosqlite.Row
    tgt_cursor = await db.execute(
        "SELECT os, privilege_level FROM targets WHERE id = ?",
        (target_id,),
    )
    tgt_row = await tgt_cursor.fetchone()
    env = {
        "os": tgt_row["os"] if tgt_row else "unknown",
        "privilege_level": tgt_row["privilege_level"] if tgt_row else "unknown",
        "engine": engine,
    }

    # 從 result 推斷 commands_executed
    commands = []
    if hasattr(result, "commands") and result.commands:
        commands = result.commands
    elif result.output:
        # 嘗試從 output 中提取指令行（以 $ 或 # 開頭的行）
        for line in (result.output or "").split("\n"):
            stripped = line.strip()
            if stripped.startswith(("$ ", "# ", ">>> ")):
                commands.append(stripped.lstrip("$# >").strip())
    if not commands:
        commands = [f"(executed via {engine})"]

    poc = PoCRecord(
        technique_id=technique_id,
        target_ip=target_ip,
        commands_executed=commands,
        input_params={"engine": engine},
        output_snippet=(result.output or "")[:1000],
        environment=env,
        reproducible=bool(result.output),
    )

    fact_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO facts "
            "(id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id, score, collected_at) "
            "VALUES (?, ?, ?, 'poc', ?, ?, ?, 1, ?)",
            (
                fact_id, f"poc.{technique_id}", poc.to_json(),
                technique_id, target_id, operation_id, now,
            ),
        )
        await db.commit()
    except Exception:
        pass  # INSERT OR IGNORE 處理重複
```

**Metasploit 成功路徑的 PoC 記錄（`_execute_metasploit`）：**

在 `_execute_metasploit` 的 `if status == "success":` 區塊末尾新增：

```python
# B1: Record PoC for Metasploit exploit
from app.models.poc_record import PoCRecord
poc = PoCRecord(
    technique_id=technique_id,
    target_ip=target_ip,
    commands_executed=[f"metasploit:{service_name}"],
    input_params={"service": service_name, "engine": "metasploit"},
    output_snippet=(output or "")[:1000],
    environment={"engine": "metasploit", "service": service_name},
    reproducible=True,
)
poc_fact_id = str(uuid.uuid4())
await db.execute(
    "INSERT OR IGNORE INTO facts "
    "(id, trait, value, category, source_technique_id, "
    "source_target_id, operation_id, score, collected_at) "
    "VALUES (?, ?, ?, 'poc', ?, ?, ?, 1, ?)",
    (poc_fact_id, f"poc.{technique_id}", poc.to_json(),
     technique_id, target_id, operation_id, completed_ts),
)
```

### B1 — PoC 報告 API

**新增路由（`backend/app/routers/operations.py` 或新增 `backend/app/routers/poc.py`）：**

```python
@router.get("/api/operations/{operation_id}/poc")
async def get_poc_records(operation_id: str, db=Depends(get_db)):
    """取得指定 operation 的所有 PoC 記錄。"""
    # 確認 operation 存在
    cursor = await db.execute(
        "SELECT id FROM operations WHERE id = ?", (operation_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")

    # 查詢 poc.* facts
    cursor = await db.execute(
        "SELECT trait, value, source_target_id, collected_at "
        "FROM facts WHERE operation_id = ? AND trait LIKE 'poc.%' "
        "ORDER BY collected_at DESC",
        (operation_id,),
    )
    rows = await cursor.fetchall()

    poc_records = []
    for row in rows:
        try:
            record = json.loads(row["value"])
            poc_records.append(record)
        except json.JSONDecodeError:
            continue

    return {
        "operation_id": operation_id,
        "poc_records": poc_records,
        "total": len(poc_records),
    }
```

### Orient Prompt 排除 PoC Facts

在 `orient_engine.py` 的 `_format_categorized_facts` 中新增排除條件：

```python
# 排除 PoC facts（避免 prompt 膨脹）
if trait.startswith("poc."):
    continue
```

---

## ✅ 驗收標準（Done When）

### Phase 1 — Security Skills Library (A3)

- [ ] `backend/app/data/skills/` 目錄已建立，包含 8 個 Markdown skill 檔案
- [ ] 每個 skill 檔案包含 YAML front matter（title, applicable_techniques, mitre_tactics）
- [ ] `SkillLoader.load_skills()` 根據 technique_id 正確匹配並回傳 skill 內容
- [ ] 父級匹配生效：`load_skills("T1003.001")` 回傳 `credential_dumping.md` 內容
- [ ] Tactic fallback 生效：無精確匹配時使用 `_TACTIC_SKILL_FALLBACK`
- [ ] 每次最多載入 2 個 skill（`_MAX_SKILLS_PER_CALL` 限制）
- [ ] 每個 skill 截取上限 3200 字元（`_MAX_CHARS_PER_SKILL`）
- [ ] Orient prompt 成功注入 `## 8.5. RELEVANT SECURITY KNOWLEDGE` section
- [ ] Skill 檔案不存在時 Orient 照常運作（空字串回傳，無 exception）
- [ ] `make test-filter FILTER=test_skill_loader` 全數通過

### Phase 2 — PoC Auto Generation (B1)

- [ ] `PoCRecord` dataclass 定義完成，含 `to_json()` / `from_json()` 方法
- [ ] `FactCategory` enum 新增 `POC = "poc"`
- [ ] `_finalize_execution` 成功路徑自動呼叫 `_record_poc()`
- [ ] `_execute_metasploit` 成功路徑自動記錄 PoC fact
- [ ] PoC fact 使用 `trait = poc.{technique_id}` 格式儲存
- [ ] PoC fact value 為合法 JSON，可透過 `PoCRecord.from_json()` 反序列化
- [ ] `GET /api/operations/{id}/poc` 回傳正確的 PoC 列表
- [ ] 空 PoC 時回傳 `{"poc_records": [], "total": 0}`
- [ ] Operation 不存在時回傳 404
- [ ] Orient `_format_categorized_facts` 排除 `poc.*` trait
- [ ] Attack Graph 忽略 `poc.*` trait
- [ ] `make test-filter FILTER=test_poc` 全數通過

### 整合驗證

- [ ] `make test` 全數通過（不引入新的 test failure）
- [ ] `make lint` 無 error
- [ ] 前端 Operation Detail 可顯示 PoC 列表（至少有 UI 區塊，可延後 polish）

---

## 🚫 禁止事項（Out of Scope）

- 不要修改 DB schema（使用現有 facts 表，不新增 poc 專用表）
- 不要修改 Orient 的 JSON output schema（`options` 結構不變）
- 不要在 skill 檔案中包含實際 exploit payload 或 shellcode
- 不要引入新的 Python 依賴
- 不要在 PoC 記錄中儲存完整 credential 明文（`input_params.credential` 應遮罩處理：`admin:P***`）
- 不要實作 PoC 的自動重放功能（超出範圍，可作為後續 SPEC）
- 不要修改 OODA 迭代間隔或 Orient 的 confidence 計算邏輯

---

## 📎 參考資料（References）

- 概念來源：CyberStrikeAI A3（Security Skills Library）、Strix B1（PoC Auto Generation）
- 現有類似實作：
  - `backend/app/services/orient_engine.py` — Orient prompt 組裝（skill 注入點）
  - `backend/app/services/engine_router.py` — `_finalize_execution()`（PoC 記錄點）
  - `backend/app/services/fact_collector.py` — fact 儲存模式（PoC 沿用）
  - `backend/app/models/enums.py` — `FactCategory` enum
- 關鍵檔案：
  - `backend/app/services/skill_loader.py` — 新增：Skill 載入模組
  - `backend/app/data/skills/*.md` — 新增：Skill 檔案目錄
  - `backend/app/models/poc_record.py` — 新增：PoCRecord dataclass
  - `backend/app/routers/operations.py` — 新增 PoC API endpoint
  - `backend/app/services/orient_engine.py` — 修改：注入 skill section + 排除 poc facts
  - `backend/app/services/engine_router.py` — 修改：`_finalize_execution` + `_execute_metasploit` 新增 PoC 記錄


