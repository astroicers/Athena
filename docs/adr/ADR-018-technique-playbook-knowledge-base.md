# [ADR-018]: Technique Playbook 知識庫架構

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-02 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

使用者提出需求：「找大量的 payload 建立 kill chain 或 MITRE ATT&CK 的文本，讓 Athena 參考」。

此需求對應兩個不同層次：
1. **執行層（DirectSSHEngine）**：MITRE technique ID → Shell 命令映射
2. **決策層（OrientEngine）**：AI 推薦時有實際可執行命令庫的背書

現有架構的問題：
- OrientEngine 推薦技術時，不知道哪些技術實際上有 Shell 命令實作
- 可能推薦 Athena 無法執行的技術

---

## 決策（Decision）

採用**雙層知識庫架構**：

### 層次 A：SQLite `technique_playbooks` 表（執行層）

```sql
CREATE TABLE IF NOT EXISTS technique_playbooks (
    id TEXT PRIMARY KEY,
    mitre_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'linux',
    command TEXT NOT NULL,
    output_parser TEXT,
    facts_traits TEXT NOT NULL DEFAULT '[]',
    source TEXT DEFAULT 'seed',
    tags TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);
```

初始 seed：13 個 Linux technique，可透過 API 或 import 腳本擴充。

### 層次 B：OrientEngine Section 7.6（決策層）

在 `_build_prompt()` 中新增可用 playbook 摘要，讓 LLM 知道哪些技術實際上可執行：

```
## 7.6. AVAILABLE TECHNIQUE PLAYBOOKS
T1046 (Network Service Discovery) — available via DirectSSH
T1003.001 (OS Credential Dumping) — available via DirectSSH [high-value]
...
```

---

## 擴充路徑

| 來源 | 方式 | 優先度 |
|------|------|--------|
| PayloadsAllTheThings（GitHub） | 解析 Markdown → import 腳本 | 中期 |
| MITRE ATT&CK STIX JSON | 官方 technique procedures | 長期 |
| 使用者自定義 | `POST /api/playbooks` API endpoint | 短期 ✅ |
| 批次匯入 | `POST /api/playbooks/bulk` endpoint | 短期 ✅ |
| 內建 Seed 擴充 | 124 playbooks covering 14 ATT&CK tactics | 短期 ✅ |

---

## 後果（Consequences）

**正面影響：**
- DirectSSHEngine 有 DB 後援，命令庫可在不重啟服務的情況下擴充
- OrientEngine 推薦更精準（只推薦實際可執行的技術）
- 為未來 PayloadsAllTheThings 大量 payload 匯入奠定基礎

**技術債：**
- ✅ Layer B（OrientEngine Section 7.6）已實作 — `orient_engine.py` L500-514，查詢 `technique_playbooks` 依平台篩選並注入 `{playbook_summary}` 至提示詞
- ✅ `POST /api/playbooks` API endpoint 已實作 — `routers/playbooks.py`
- ✅ `POST /api/playbooks/bulk` 批次匯入 API 已實作
- ✅ Layer C：Seed 擴充至 124 個 playbook（62 Linux + 62 Windows），覆蓋全 14 個 ATT&CK tactics

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：ADR-017（DirectSSHEngine 使用此知識庫）、ADR-005（OrientEngine 提示詞架構）
