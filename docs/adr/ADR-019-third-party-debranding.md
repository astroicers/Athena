# [ADR-019]: 第三方專案識別符去識別化策略

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-02 |
| **決策者** | 專案負責人 |

---

## 背景（Context）

Athena 在設計時借鑒了三個開源專案的架構理念：

| 專案 | 授權 | 借鑒內容 | 實際依賴 |
|------|------|---------|---------|
| MITRE Caldera | Apache 2.0 | C2 框架 ability/agent 架構概念 | HTTP API 呼叫（C2EngineClient） |
| Shannon | AGPL-3.0 | AI 自適應執行引擎概念 | 無（已 Deprecated，從未呼叫） |
| PentestGPT (GreyDGL) | MIT | AI 滲透測試推理方法論 | 無（OrientEngine 完全自研） |

上述三個專案在 Athena 中均為**概念借鑒**，無任何程式碼 import 或 derivative work 關係。
然而程式碼庫中存在大量以這些專案命名的識別符（class 名稱、環境變數、API key），
可能造成外界認為 Athena 直接依賴或使用這些工具。

---

## 授權分析

| 授權類型 | 去識別化合規性 |
|---------|--------------|
| **Apache 2.0 (Caldera)** | 無強制要求在程式碼中保留原始專案名稱；Athena 非 fork，無 NOTICE 義務 |
| **AGPL-3.0 (Shannon)** | Shannon 已 Deprecated（`SHANNON_URL` 從未呼叫）；API 隔離已在 ADR-006 確認；去識別化不影響合規性 |
| **MIT (PentestGPT)** | 最寬鬆授權；Athena 未 import 任何 PentestGPT 程式碼；去識別化完全合規 |

**結論**：可合規地以通用術語替換所有第三方專案名稱，並在 README 的致謝區塊中說明概念借鑒來源。

---

## 決策（Decision）

### 識別符映射表

#### 檔案重命名

| 原始路徑 | 新路徑 |
|---------|-------|
| `backend/app/clients/caldera_client.py` | `backend/app/clients/c2_client.py` |
| `backend/app/clients/mock_caldera_client.py` | `backend/app/clients/mock_c2_client.py` |
| `backend/app/clients/shannon_client.py` | `backend/app/clients/ai_engine_client.py` |

#### Python 類別 / 函數識別符

| 原始名稱 | 新名稱 | 備注 |
|---------|-------|------|
| `CalderaClient` | `C2EngineClient` | |
| `MockCalderaClient` | `MockC2Client` | |
| `ShannonClient` | `AiEngineClient` | |
| `PentestGPTRecommendation` | `OrientRecommendation` | 後端 + 前端同步 |
| `SUPPORTED_CALDERA_VERSIONS` | `SUPPORTED_C2_VERSIONS` | |

#### 環境變數

| 原始名稱 | 新名稱 |
|---------|-------|
| `CALDERA_URL` | `C2_ENGINE_URL` |
| `CALDERA_API_KEY` | `C2_ENGINE_API_KEY` |
| `CALDERA_AGENT_CALLBACK_URL` | `C2_AGENT_CALLBACK_URL` |
| `MOCK_CALDERA` | `MOCK_C2_ENGINE` |
| `CALDERA_MOCK_BEACON` | `C2_MOCK_BEACON` |
| `SHANNON_URL` | `AI_ENGINE_URL` |

#### ExecutionEngine Enum（~~名稱改、值不變~~ → Rev 2：值也替換）

> **Rev 2 修訂**：實作時決定徹底替換 enum 底層值並刪除 Shannon，避免留下殘留識別符。
> 以 DB migration（`try/except pass` 模式）確保向後相容。

```python
# 改前
class ExecutionEngine(str, Enum):
    CALDERA = "caldera"
    SHANNON = "shannon"

# Rev 1 計劃（未採用）
class ExecutionEngine(str, Enum):
    C2 = "caldera"        # 值不變
    ADAPTIVE = "shannon"  # 值不變

# Rev 2 實際實作（2026-03-04）
class ExecutionEngine(str, Enum):
    SSH = "ssh"
    PERSISTENT_SSH = "persistent_ssh"
    C2 = "c2"
    MOCK = "mock"
    METASPLOIT = "metasploit"
    WINRM = "winrm"
```

前端 TypeScript enum 同步更新。

#### DB Schema 遷移（Rev 2 新增）

| 遷移類型 | SQL |
|---------|-----|
| 欄位重命名 | `ALTER TABLE techniques RENAME COLUMN caldera_ability_id TO c2_ability_id` |
| 值遷移 | `UPDATE techniques SET engine='ssh' WHERE engine='caldera'` |
| 值遷移 | `UPDATE technique_executions SET engine='ssh' WHERE engine='caldera'` |
| 值遷移 | `UPDATE mission_steps SET engine='ssh' WHERE engine='caldera'` |
| 預設值 | `engine DEFAULT 'ssh'`（原 `'caldera'`） |

遷移採用 `try/except pass` 模式，冪等可重複執行。

#### Shannon / AiEngineClient 完全移除（Rev 2 新增）

- `backend/app/clients/ai_engine_client.py` — **刪除**（非重命名）
- Shannon 從未在生產環境中啟用，無需保留
- `health.py` 中 `ai_engine` 狀態區塊移除
- `EngineRouter` 建構子移除 `adaptive_engine` 參數
- `config.py` 移除 `AI_ENGINE_URL` 設定

#### Health API JSON Key

```python
# 改前
services = {"caldera": ..., "shannon": ...}

# Rev 1 計劃
services = {"c2_engine": ..., "ai_engine": ...}

# Rev 2 實際實作（ai_engine 移除）
services = {"c2_engine": ...}
```

同步更新 `test_spec_004_api.py` 的驗證邏輯。

### README 致謝區塊

在 README 授權區塊之前新增：

```markdown
## 致謝與靈感來源

Athena 在設計過程中受到以下開源專案的啟發：

- **MITRE ATT&CK 框架** — 戰術/技術/程序知識庫（CC BY 4.0）
- **MITRE Caldera** — C2 框架架構設計理念（Apache 2.0，僅架構借鑒，無程式碼依賴）
- **PentestGPT** (GreyDGL) — AI 輔助滲透測試推理方法論（MIT，僅概念借鑒，無程式碼依賴）

Athena 核心程式碼為完全自主實作，不包含上述專案的任何程式碼。
```

---

## 後果（Consequences）

**正面影響：**
- 程式碼庫不再包含可識別的第三方工具名稱
- 減少外界對 Athena 授權狀態的疑慮
- README 致謝說明符合開源社群慣例，同時明確宣告無程式碼依賴

**技術考量：**
- ~~Enum 底層值保持不變~~ → Rev 2：值全面替換為實際引擎名稱（ssh/c2/mock/metasploit/winrm/persistent_ssh）
- DB 遷移以 `try/except pass` 冪等模式實作，既有資料自動轉換
- Shannon（AiEngineClient）完全刪除，不再保留空殼
- `MOCK_CALDERA` 環境變數重命名為 `MOCK_C2_ENGINE`，CI/CD 環境需同步更新
- `test_spec_004_api.py` health key 驗證與 health.py 同步修改（移除 `ai_engine`）
- 影響約 30+ 檔案（後端 services、routers、tests、前端 types、enums、components）

**不修改的位置：**
- 歷史 ADR 文件正文（ADR-005、ADR-006）— 歷史決策記錄應保留，已有 Rev 1 澄清

---

## 關聯（Relations）

- 參考：ADR-006（執行引擎授權隔離）、ADR-005（Orient 引擎）、ADR-001（技術棧）
- 補充：ADR-017（DirectSSHEngine）、ADR-018（Technique Playbook）

---

## 修訂記錄（Revision History）

- **Rev 1**（2026-03-02）：首次建立。識別符重命名策略，Enum 底層值不變。
- **Rev 2**（2026-03-04）：深度去識別化。Enum 底層值全面替換為實際引擎名（ssh/c2/mock 等六值）；DB column `caldera_ability_id` → `c2_ability_id`（含遷移）；Shannon/AiEngineClient 完全刪除；Health API `ai_engine` key 移除。影響 30+ 檔案，224 pytest + 63 vitest 全數通過。
