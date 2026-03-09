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

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| Skill 內容注入 Orient prompt | Orient LLM 回應 | 推薦品質提升，reasoning_text 引用 skill 知識；prompt token 量增加（每 skill 約 400-800 tokens） |
| `poc.*` fact 插入 facts 表 | Observe 階段 fact 統計 | PoC fact 納入 fact count，但 Orient summarize 不應將 PoC 當作一般情報 |
| `poc.*` fact 插入 facts 表 | Orient categorized_facts | 需排除 `poc.*` trait（避免 prompt 膨脹） |
| `poc.*` fact 插入 facts 表 | Attack Graph fact processing | Attack Graph 應忽略 `poc.*` trait（非攻擊路徑節點） |
| FactCategory 新增 `POC` | FactCategory enum | 需更新 `app/models/enums.py` 新增 `POC = "poc"` |
| 新增 `/api/operations/{id}/poc` | 前端 OperationDetail | 前端新增 PoC 區塊顯示 PoC 列表 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：Skill 檔案不存在或格式錯誤 — `SkillLoader` 回傳空字串，Orient 照常運作無 skill section
- **Case 2**：同一 technique 對應多個 skill（如 `T1190` → `sql_injection` + `xss`）— 只取前 2 個（已受 max 2 限制），按 `_SKILL_TECHNIQUE_MAP` 列表順序
- **Case 3**：PoC 產出時 `result.output` 為空 — `output_snippet` 設為空字串，`reproducible` 設為 `False`
- **Case 4**：同一 technique 對同一 target 執行多次成功 — 每次都產出獨立的 PoC fact（`INSERT OR IGNORE` 防重複 trait+value 組合）
- **Case 5**：Metasploit 成功路徑的 PoC 記錄 — `_execute_metasploit` 成功後同樣記錄 PoC，`commands_executed` 為 exploit module 路徑
- **Case 6**：`commands_executed` 資訊不可得（如 mock engine）— 設為 `["(mock execution)"]`，`reproducible` 設為 `False`
- **Case 7**：Skill 檔案超過 token budget — 截取前 800 tokens（以字元估算：約 3200 字元）

### 回退方案（Rollback Plan）

- **回退方式**：revert commit
- **不可逆評估**：完全可逆。Skill 檔案為靜態 Markdown，刪除即可。`poc.*` facts 在 revert 後不影響既有功能（trait 前綴隔離）
- **資料影響**：回退後已產出的 `poc.*` facts 保留在 DB 中不會造成問題，可透過 `DELETE FROM facts WHERE trait LIKE 'poc.%'` 清理

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
