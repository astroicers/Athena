# SPEC-016：工具容器標準化 I/O 規格

> 定義所有工具容器與 Athena ContainerEngineClient 之間的輸入/輸出合約。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-016 |
| **狀態** | `Planned`（尚未實作）— `ContainerEngineClient` 不存在，本規格為未來功能設計文件 |
| **關聯 ADR** | ADR-006（執行引擎抽象層與授權隔離） |
| **關聯 SPEC** | SPEC-008（執行引擎客戶端） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 目標（Goal）

定義工具容器的標準化 I/O 合約，使任何符合規格的容器都能被 Athena 的 `ContainerEngineClient` 執行，輸出直接對齊 `ExecutionResult` 並被 `FactCollector` 消費。

**設計原則：**

1. **對齊現有合約** — 輸出格式直接映射 `ExecutionResult`（SPEC-008）
2. **分層 I/O** — 基礎層（環境變數 + JSON stdout）零依賴；擴展層（volume mount）支援檔案/產物
3. **Trait 命名可推導** — 遵循 `fact_collector._category_from_trait()` 的推導邏輯
4. **自包含** — 每個容器獨立運行，不依賴其他容器或外部服務
5. **向後相容** — 只使用基礎層的簡單工具不受擴展層影響

---

## 架構位置

```
OODA ACT Phase
  → EngineRouter.select_engine()
    → engine == "container"
      → ContainerEngineClient.execute(ability_id, target, params)
        → docker run -e TOOL_INPUT_TARGET=... -v input:/input -v output:/output image_name
          → 容器 stdout (JSON) → 解析為 ExecutionResult    ← 基礎層 (facts)
          → /output/manifest.json → 解析為 Artifacts       ← 擴展層 (產物)
            → FactCollector.collect_from_result()
              → Facts 表 + Artifacts 儲存
```

```
BaseEngineClient (SPEC-008)
├── CalderaClient          — MITRE Caldera REST API
├── ShannonClient          — Shannon AI Engine API
├── MockCalderaClient      — 開發/測試用 Mock
└── ContainerEngineClient  — 本規格定義的容器執行引擎 (新增)
```

---

## 輸入合約（Container Input Contract）

工具容器透過 **兩層輸入通道** 接收資料：

```
輸入通道
├── 基礎層：環境變數 — 簡單值 (target, params, flags)
└── 擴展層：/input/ volume — 檔案與資料夾 (wordlist, config, 前步產出)
```

### 基礎層：環境變數

#### 必要環境變數

| 環境變數 | 型別 | 說明 | 範例 |
|----------|------|------|------|
| `TOOL_INPUT_TARGET` | string | 主要目標（域名、IP、URL） | `example.com`, `10.0.1.5` |
| `TOOL_INPUT_ABILITY_ID` | string | 對應的 MITRE ATT&CK 技術 ID | `T1595.001`, `T1046` |
| `TOOL_EXECUTION_ID` | string | Athena 分配的執行 ID | `exec-a1b2c3d4` |

#### 選用環境變數

| 環境變數 | 型別 | 說明 | 範例 |
|----------|------|------|------|
| `TOOL_INPUT_PARAMS` | JSON string | 額外參數 | `{"ports":"1-1000","timeout":30}` |
| `TOOL_TIMEOUT` | integer | 最大執行秒數（預設 120） | `300` |

### 擴展層：`/input/` Volume Mount

當工具需要檔案輸入時（wordlist、config、前一步工具的產出），`ContainerEngineClient` 將檔案掛載至容器內的 `/input/` 目錄。

#### `/input/` 目錄結構

```
/input/
├── targets.txt          # 批次目標清單（前步產出的子域名、IP 清單等）
├── wordlists/           # 字典檔
│   └── common.txt
├── config/              # 工具專屬配置
│   └── nmap-scripts.nse
└── previous/            # 前步工具的原始產出
    └── subfinder.json
```

#### 檔案輸入環境變數

| 環境變數 | 型別 | 說明 | 範例 |
|----------|------|------|------|
| `TOOL_INPUT_FILE` | string | 主要輸入檔案路徑 | `/input/targets.txt` |
| `TOOL_INPUT_DIR` | string | 輸入資料夾路徑 | `/input/previous/` |
| `TOOL_INPUT_WORDLIST` | string | 字典檔路徑 | `/input/wordlists/common.txt` |
| `TOOL_INPUT_CONFIG` | string | 配置檔路徑 | `/input/config/tool.yaml` |

#### 使用場景

| 場景 | 輸入方式 | 說明 |
|------|----------|------|
| subfinder 掃描單一域名 | `TOOL_INPUT_TARGET=example.com` | 僅需基礎層 |
| gobuster 需要 wordlist | `TOOL_INPUT_TARGET` + `/input/wordlists/` | 基礎層 + 擴展層 |
| nmap 掃描前步發現的子域名 | `TOOL_INPUT_FILE=/input/targets.txt` | 擴展層（批次輸入） |
| sqlmap 需要 HTTP request 檔 | `TOOL_INPUT_FILE=/input/request.txt` | 擴展層（複雜輸入） |
| nuclei 自定義 template | `TOOL_INPUT_DIR=/input/templates/` | 擴展層（資料夾輸入） |

#### Workflow 串接：前步產出 → 後步輸入

`ContainerEngineClient` 負責將前步工具的 `/output/` 產物掛載為後步工具的 `/input/previous/`：

```
Tool A: subfinder
  /output/subdomains.txt  ← subfinder 產出子域名清單
        │
        ▼ ContainerEngineClient 自動串接
Tool B: nmap
  /input/targets.txt      ← 掛載 Tool A 的產出
  TOOL_INPUT_FILE=/input/targets.txt
```

### 設計理由

- **環境變數優於命令列參數**：避免 shell injection，Docker SDK 安全注入
- **環境變數優於 stdin**：Docker 非 TTY 模式下 stdin 行為不一致
- **`/input/` volume 補充環境變數**：大型檔案（wordlist 數 MB）和二進位檔案無法透過環境變數傳遞
- **固定掛載點 `/input/`**：容器內路徑統一，不依賴主機目錄結構

---

## 輸出合約（Container Output Contract）

工具容器透過 **兩層輸出通道** 產出結果：

```
輸出通道
├── 基礎層：stdout JSON — 結構化 facts + 摘要 (必要)
└── 擴展層：/output/ volume — 完整報告、二進位產物、大型檔案 (選用)
```

### 基礎層：stdout JSON

工具容器必須將 **單一 JSON 物件** 寫入 **stdout**。此 JSON 直接映射 Athena 的 `ExecutionResult`。

### JSON 輸出格式

```json
{
  "success": true,
  "output": "Human-readable summary of execution results",
  "facts": [
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "network.host.ip", "value": "10.0.1.6"},
    {"trait": "service.port", "value": "10.0.1.5:443/https"}
  ],
  "error": null
}
```

### 欄位定義

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `success` | boolean | 是 | 工具是否成功完成 |
| `output` | string \| null | 是 | 人類可讀的執行摘要，用於 `result_summary` 和 Orient 分析上下文 |
| `facts` | array | 是 | 結構化情報列表（可為空陣列 `[]`） |
| `facts[].trait` | string | 是 | 點分層級識別碼，遵循 Trait 命名規範 |
| `facts[].value` | string | 是 | 實際資料值，最大 500 字元（超出截斷） |
| `error` | string \| null | 是 | 失敗時的錯誤訊息 |

### 映射至 ExecutionResult

```python
# ContainerEngineClient 內部轉換（虛擬碼）
container_output = json.loads(stdout)
result = ExecutionResult(
    success=container_output["success"],
    execution_id=execution_id,       # 由 ContainerEngineClient 注入
    output=container_output["output"],
    facts=container_output["facts"],  # 直接透傳
    error=container_output["error"],
)
```

### 輸出規則

1. **stdout 只輸出 JSON** — 工具的 log、debug、進度訊息一律寫入 stderr
2. **單一 JSON 物件** — 不是 JSONL，不是陣列，是一個完整的 JSON 物件
3. **UTF-8 編碼** — 所有字串使用 UTF-8
4. **facts 值必須為字串** — 數字、布林等一律轉為字串（`"443"` 非 `443`）
5. **失敗時也輸出 JSON** — `{"success": false, "output": null, "facts": [], "error": "reason"}`

---

### 擴展層：`/output/` Volume — Artifact 產物

當工具產出超越 JSON facts 的內容（完整報告、二進位檔案、大型資料集），應寫入 `/output/` 目錄並附上 `manifest.json`。

#### `/output/` 目錄結構

```
/output/
├── manifest.json           # 產物清單（必要，描述所有產物）
├── scan-report.xml         # nmap 完整 XML 報告
├── screenshots/            # 截圖資料夾
│   ├── login-page.png
│   └── admin-panel.png
└── loot/                   # 擷取的檔案
    └── shadow.txt
```

#### `manifest.json` 格式

```json
{
  "artifacts": [
    {
      "name": "scan-report.xml",
      "path": "scan-report.xml",
      "media_type": "application/xml",
      "size_bytes": 45230,
      "description": "Nmap full TCP scan XML report",
      "category": "report"
    },
    {
      "name": "login-page.png",
      "path": "screenshots/login-page.png",
      "media_type": "image/png",
      "size_bytes": 128400,
      "description": "Screenshot of target login page",
      "category": "evidence"
    },
    {
      "name": "shadow.txt",
      "path": "loot/shadow.txt",
      "media_type": "text/plain",
      "size_bytes": 1024,
      "description": "Extracted /etc/shadow file",
      "category": "loot"
    }
  ]
}
```

#### Artifact 欄位定義

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `name` | string | 是 | 產物顯示名稱 |
| `path` | string | 是 | 相對於 `/output/` 的檔案路徑 |
| `media_type` | string | 是 | MIME type（RFC 6838） |
| `size_bytes` | integer | 是 | 檔案大小（bytes） |
| `description` | string | 否 | 人類可讀描述 |
| `category` | string | 是 | 產物分類（見下表） |

#### Artifact Category

| Category | 說明 | 範例 |
|----------|------|------|
| `report` | 工具原生報告 | nmap XML, nuclei JSON report, nikto HTML |
| `evidence` | 視覺證據 | 截圖、錄影、網頁快照 |
| `loot` | 擷取的敏感檔案 | /etc/shadow, SAM database, config files |
| `data` | 結構化資料集 | 子域名完整清單 CSV, port scan 結果 |
| `log` | 工具完整日誌 | 執行 debug log, 詳細掃描記錄 |
| `archive` | 打包多檔案 | 掃描結果 ZIP, 多工具產出合併 |

#### 基礎層 vs 擴展層的分工

| 資料特性 | 基礎層 (stdout JSON) | 擴展層 (/output/) |
|----------|---------------------|-------------------|
| 結構化情報 (facts) | `facts[]` 陣列 | 不放 |
| 人類可讀摘要 | `output` 欄位 | 不放 |
| 工具原生報告 (XML/HTML) | 不放（超過 500 字元會截斷） | `report` category |
| 二進位檔案 (pcap/png/dump) | 不放 | `evidence` 或 `loot` |
| 大型資料集 (>500 字元) | 摘要放 `output`，引用 artifact | `data` category |
| 前步→後步串接資料 | 不適用 | `data` category → 掛載為後步 `/input/` |

#### 簡單工具可以不用擴展層

只產出 JSON facts 的工具（如 subfinder）不需要 `/output/` 目錄和 manifest.json。`ContainerEngineClient` 檢查 `/output/manifest.json` 是否存在，不存在則跳過 artifact 處理。

---

## 輸出格式規範

工具容器可產出多種格式，每種格式有明確用途：

| 格式 | 通道 | 用途 | 消費者 |
|------|------|------|--------|
| **JSON** | stdout (基礎層) | 結構化 facts | `FactCollector` |
| **JSON** | /output/ (擴展層) | 完整結構化報告 | Artifact 儲存 + Orient 分析 |
| **XML** | /output/ | 工具原生報告（nmap, Burp） | Artifact 儲存 |
| **HTML** | /output/ | 人類可讀報告（nikto, OWASP ZAP） | Artifact 儲存 + 前端展示 |
| **CSV** | /output/ | 大型資料集 | Artifact 儲存 + 批次處理 |
| **Plaintext** | /output/ | 工具日誌、raw output | Artifact 儲存 |
| **Binary** | /output/ | pcap、memory dump、截圖 | Artifact 儲存 |
| **ZIP** | /output/ | 多檔案打包 | Artifact 解壓 + 儲存 |

### JSON stdout 與 /output/ JSON 的差異

```
stdout JSON (基礎層)                /output/*.json (擴展層)
─────────────────                   ──────────────────────
必須遵循 ExecutionResult 格式        自由格式，由 manifest 描述
facts 值最多 500 字元               無大小限制
供 FactCollector 自動處理            供 Artifact 儲存與人類檢視
每次執行只有一個 JSON               可有多個 JSON 檔案
```

---

## Athena 側所需的架構擴充（未來實作）

擴展層需要 Athena 側的配合修改，此處列出供未來實作參考：

### 1. `ExecutionResult` 擴充

```python
# backend/app/clients/__init__.py — 建議新增
@dataclass
class ExecutionArtifact:
    id: str
    name: str
    path: str                    # 相對於 /output/ 的路徑
    media_type: str              # MIME type
    size_bytes: int
    description: str | None = None
    category: str = "data"       # report/evidence/loot/data/log/archive
    storage_url: str | None = None  # 持久化後的儲存位置

@dataclass
class ExecutionResult:
    success: bool
    execution_id: str
    output: str | None = None
    facts: list[dict] = field(default_factory=list)
    artifacts: list[ExecutionArtifact] = field(default_factory=list)  # 新增
    error: str | None = None
```

### 2. Database `artifacts` 表

```sql
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    technique_execution_id TEXT REFERENCES technique_executions(id) ON DELETE CASCADE,
    operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'data',
    storage_path TEXT NOT NULL,       -- 本地檔案路徑或 S3 URL
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3. `EngineRouter.execute()` 傳遞 params

```python
# backend/app/services/engine_router.py — 需修改
async def execute(
    self, db, technique_id, target_id, engine, operation_id,
    ooda_iteration_id=None,
    params: dict | None = None,    # 新增
) -> dict:
    # ...
    result = await client.execute(ability_id, target_label, params)  # 傳遞 params
```

### 4. `FactCollector` 處理 artifact 參照

```python
# 當 fact value 指向 artifact 時，使用特殊 trait
# 例如：{"trait": "file.artifact", "value": "artifact://exec-123/scan-report.xml"}
# FactCollector 識別 artifact:// 協議，建立 fact → artifact 關聯
```

---

## Trait 命名規範

Trait 使用點分層級命名 (`category.subcategory.field`)，首段必須對齊 `FactCategory`，使 `fact_collector._category_from_trait()` 能自動推導分類。

### Trait 命名對應表

| FactCategory | Trait 前綴 | 範例 trait | 範例 value |
|-------------|-----------|-----------|-----------|
| `NETWORK` | `network.*` | `network.host.ip` | `10.0.1.5` |
| | | `network.host.hostname` | `dc-01.corp.local` |
| | | `network.subnet` | `10.0.1.0/24` |
| | | `network.dns.record` | `A:example.com:10.0.1.5` |
| `SERVICE` | `service.*` | `service.port` | `10.0.1.5:443/https` |
| | | `service.technology` | `Apache/2.4.52` |
| | | `service.url` | `https://example.com/admin` |
| | | `service.banner` | `SSH-2.0-OpenSSH_8.9` |
| `HOST` | `host.*` | `host.os` | `Windows Server 2019` |
| | | `host.user.name` | `CORP\\Administrator` |
| | | `host.process` | `lsass.exe (PID 672)` |
| | | `host.session` | `RDP:Administrator@DC-01` |
| `CREDENTIAL` | `credential.*` | `credential.hash` | `Administrator:aad3b435...` |
| | | `credential.password` | `P@ssw0rd123` |
| | | `credential.token` | `eyJhbGciOi...` |
| | | `credential.certificate` | `CN=corp.local` |
| `VULNERABILITY` | `vulnerability.*` | `vulnerability.cve` | `CVE-2024-1234` |
| | | `vulnerability.finding` | `SQL Injection in /login` |
| | | `vulnerability.severity` | `CRITICAL` |
| `FILE` | `file.*` | `file.path` | `/etc/shadow` |
| | | `file.content` | `root:$6$xyz...` |
| | | `file.secret` | `AWS_ACCESS_KEY=AKIA...` |

### 命名規則

1. **全小寫** — `network.host.ip` 非 `Network.Host.IP`
2. **點分層級** — 至少兩層 `category.field`，建議三層 `category.subcategory.field`
3. **首段對齊 FactCategory** — 確保 `_category_from_trait()` 能正確推導
4. **子域名發現工具** — 使用 `network.host.hostname` 而非自創 trait

### 與 `_category_from_trait()` 的相容性

```python
# backend/app/services/fact_collector.py 現有邏輯
def _category_from_trait(trait: str) -> FactCategory:
    if "credential" in trait or "hash" in trait:
        return FactCategory.CREDENTIAL
    if "network" in trait or "ip" in trait:
        return FactCategory.NETWORK
    if "service" in trait or "port" in trait:
        return FactCategory.SERVICE
    if "host" in trait:
        return FactCategory.HOST
    return FactCategory.HOST
```

本規格的 trait 命名確保：
- `credential.*` → 命中 `"credential" in trait` → `CREDENTIAL`
- `network.*` → 命中 `"network" in trait` → `NETWORK`
- `service.*` → 命中 `"service" in trait` → `SERVICE`
- `host.*` → 命中 `"host" in trait` → `HOST`
- `vulnerability.*` 和 `file.*` → 需擴充 `_category_from_trait()`（見下方建議）

### 建議擴充 `_category_from_trait()`

```python
def _category_from_trait(trait: str) -> FactCategory:
    if "credential" in trait or "hash" in trait or "password" in trait:
        return FactCategory.CREDENTIAL
    if "network" in trait or "ip" in trait or "subnet" in trait or "dns" in trait:
        return FactCategory.NETWORK
    if "service" in trait or "port" in trait or "url" in trait:
        return FactCategory.SERVICE
    if "vulnerability" in trait or "cve" in trait:
        return FactCategory.VULNERABILITY
    if "file" in trait or "path" in trait:
        return FactCategory.FILE
    if "host" in trait:
        return FactCategory.HOST
    return FactCategory.HOST
```

---

## Exit Code 規範

| Exit Code | 意義 | `success` 值 | 說明 |
|-----------|------|-------------|------|
| `0` | 成功 | `true` | 工具正常完成，facts 可能為空 |
| `1` | 工具失敗 | `false` | 工具執行了但遇到錯誤（目標不可達、掃描失敗等） |
| `2` | 輸入錯誤 | `false` | 環境變數缺失或格式錯誤 |
| `3` | 超時 | `false` | 超過 `TOOL_TIMEOUT` 秒數 |

### Exit Code 與 JSON 的關係

- **Exit 0**：stdout 必須包含有效 JSON，`success: true`
- **Exit 1**：stdout 必須包含有效 JSON，`success: false`，`error` 欄位說明原因
- **Exit 2/3**：stdout 可能無 JSON 或不完整，`ContainerEngineClient` 應捕獲並生成 `ExecutionResult(success=False, error="...")`

---

## Dockerfile 規範

### 基礎映像選擇

| 工具語言 | 推薦基礎映像 | 說明 |
|----------|-------------|------|
| Go 工具 | `golang:1.22-alpine` (build) + `alpine:3.19` (runtime) | Multi-stage，最小化體積 |
| Python 工具 | `python:3.12-alpine` | 需安裝 jq 或用 Python json 模組 |
| 系統工具 | `alpine:3.19` | apk install + shell wrapper |
| 預編譯二進位 | `alpine:3.19` | 需驗證 checksum |

### Dockerfile 模板

```dockerfile
# === Stage 1: Build ===
FROM golang:1.22-alpine AS builder
RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# === Stage 2: Runtime ===
FROM alpine:3.19
RUN apk add --no-cache jq
COPY --from=builder /go/bin/subfinder /usr/local/bin/subfinder
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### Entrypoint 模板 (`entrypoint.sh`)

```bash
#!/bin/sh
set -e

# --- 輸入驗證 ---
if [ -z "${TOOL_INPUT_TARGET}" ]; then
  echo '{"success":false,"output":null,"facts":[],"error":"TOOL_INPUT_TARGET is required"}' >&1
  exit 2
fi

# --- 執行工具 (log 寫 stderr) ---
RESULT=$(subfinder -silent -d "${TOOL_INPUT_TARGET}" 2>/dev/null) || {
  echo '{"success":false,"output":null,"facts":[],"error":"subfinder execution failed"}' >&1
  exit 1
}

# --- 輸出標準化 JSON ---
echo "${RESULT}" | jq -Rsc --arg target "${TOOL_INPUT_TARGET}" '{
  success: true,
  output: ("Subdomain enumeration completed for " + $target + ". Found " + (split("\n") | map(select(length > 0)) | length | tostring) + " subdomains."),
  facts: [split("\n")[] | select(length > 0) | {trait: "network.host.hostname", value: .}],
  error: null
}'
```

### 安全性要求

1. **非 root 執行** — 建議使用 `USER nobody` 或建立專用使用者
2. **無網路外洩** — 容器僅與掃描目標通訊，不回撥其他服務
3. **無敏感資料持久化** — 容器內不寫入 credential 到檔案
4. **版本釘選** — 所有依賴使用特定版本，不用 `@latest`
5. **Checksum 驗證** — 下載預編譯二進位時必須驗證 SHA256

---

## 工具 Registry 格式

每個工具在 `backend/app/tools/registry.yaml` 中註冊 metadata，供 `ContainerEngineClient` 和 `OrientEngine` 使用。

### Registry Schema

```yaml
tools:
  - id: subfinder
    name: Subfinder
    description: "Fast passive subdomain enumeration tool"
    image: athena-tools/subfinder:1.0
    category: reconnaissance
    mitre_techniques:
      - T1595.001  # Active Scanning: Scanning IP Blocks
      - T1596      # Search Open Technical Databases
    input:
      required:
        - TOOL_INPUT_TARGET          # domain
      optional:
        - TOOL_INPUT_PARAMS          # {"sources": "crtsh,virustotal"}
    output:
      traits:
        - network.host.hostname
      artifacts: false               # 無擴展層產物
    timeout: 120
    risk_level: low

  - id: nmap
    name: Nmap
    description: "Network exploration and security auditing"
    image: athena-tools/nmap:1.0
    category: reconnaissance
    mitre_techniques:
      - T1046  # Network Service Discovery
    input:
      required:
        - TOOL_INPUT_TARGET          # IP or CIDR
      optional:
        - TOOL_INPUT_PARAMS          # {"ports": "1-1000", "scan_type": "syn"}
      files:
        - name: TOOL_INPUT_FILE      # 批次掃描目標清單
          description: "Target list from previous subdomain discovery"
          required: false
    output:
      traits:
        - network.host.ip
        - service.port
        - service.banner
        - host.os
      artifacts: true                # 產出 XML 報告
      artifact_types:
        - media_type: application/xml
          category: report
          description: "Nmap scan XML report"
    timeout: 300
    risk_level: medium

  - id: gobuster
    name: Gobuster
    description: "Directory and file brute-force tool"
    image: athena-tools/gobuster:1.0
    category: enumeration
    mitre_techniques:
      - T1083  # File and Directory Discovery
    input:
      required:
        - TOOL_INPUT_TARGET          # URL
      optional:
        - TOOL_INPUT_PARAMS          # {"extensions": "php,asp,html"}
      files:
        - name: TOOL_INPUT_WORDLIST  # 字典檔
          description: "Wordlist for directory brute-force"
          required: false
          default: "/usr/share/wordlists/dirb/common.txt"
    output:
      traits:
        - service.url
      artifacts: false
    timeout: 600
    risk_level: low

  - id: nuclei
    name: Nuclei
    description: "Fast vulnerability scanner based on templates"
    image: athena-tools/nuclei:1.0
    category: vulnerability_scanning
    mitre_techniques:
      - T1595.002  # Active Scanning: Vulnerability Scanning
    input:
      required:
        - TOOL_INPUT_TARGET          # URL
      optional:
        - TOOL_INPUT_PARAMS          # {"severity": "critical,high"}
      files:
        - name: TOOL_INPUT_DIR       # 自定義 template 資料夾
          description: "Custom nuclei templates directory"
          required: false
    output:
      traits:
        - vulnerability.cve
        - vulnerability.finding
        - vulnerability.severity
      artifacts: true
      artifact_types:
        - media_type: application/json
          category: report
          description: "Nuclei full scan report"
    timeout: 600
    risk_level: medium
```

### Registry 欄位說明

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | string | 工具唯一識別碼，對應 Docker image tag |
| `name` | string | 人類可讀名稱 |
| `description` | string | 工具描述，供 OrientEngine 使用 |
| `image` | string | Docker image 完整名稱含 tag |
| `category` | string | 工具分類：`reconnaissance`, `enumeration`, `vulnerability_scanning`, `exploitation`, `credential_access` |
| `mitre_techniques` | array | 此工具對應的 MITRE ATT&CK 技術 ID 列表 |
| `input.required` | array | 必要的環境變數名稱 |
| `input.optional` | array | 選用的環境變數名稱 |
| `input.files` | array | 檔案輸入定義（擴展層），每項含 name, description, required, default |
| `output.traits` | array | 此工具可能產出的 trait 列表 |
| `output.artifacts` | boolean | 是否產出 /output/ 擴展層產物 |
| `output.artifact_types` | array | 預期產出的 artifact 類型（media_type, category, description） |
| `timeout` | integer | 預設超時秒數 |
| `risk_level` | string | `low`, `medium`, `high`, `critical` — 供 DecisionEngine 使用 |

---

## 改造範例

### 範例 1：subfinder（子域名發現）

**改造前** (recon-pocket)：
```bash
#!/bin/sh
# 問題：輸出寫檔案、無錯誤處理、無結構化輸出
subfinder -silent -d ${1} -o /tmp/subfinder.txt
mv /tmp/subfinder.txt /subfinder/subfinder.txt
```

**改造後** (Athena 標準)：
```bash
#!/bin/sh
set -e

if [ -z "${TOOL_INPUT_TARGET}" ]; then
  echo '{"success":false,"output":null,"facts":[],"error":"TOOL_INPUT_TARGET is required"}' >&1
  exit 2
fi

RESULT=$(subfinder -silent -d "${TOOL_INPUT_TARGET}" 2>/dev/null) || {
  echo '{"success":false,"output":null,"facts":[],"error":"subfinder failed for '"${TOOL_INPUT_TARGET}"'"}' >&1
  exit 1
}

echo "${RESULT}" | jq -Rsc --arg target "${TOOL_INPUT_TARGET}" '{
  success: true,
  output: ("Subdomain enumeration for " + $target + ": found " + (split("\n") | map(select(length > 0)) | length | tostring) + " subdomains"),
  facts: [split("\n")[] | select(length > 0) | {trait: "network.host.hostname", value: .}],
  error: null
}'
```

**輸出範例：**
```json
{
  "success": true,
  "output": "Subdomain enumeration for example.com: found 3 subdomains",
  "facts": [
    {"trait": "network.host.hostname", "value": "www.example.com"},
    {"trait": "network.host.hostname", "value": "api.example.com"},
    {"trait": "network.host.hostname", "value": "mail.example.com"}
  ],
  "error": null
}
```

### 範例 2：nmap（網路掃描 — 基礎層 + 擴展層）

展示同時使用 JSON stdout (facts) 和 /output/ (XML 報告) 的完整範例。

**改造後** (Athena 標準)：
```bash
#!/bin/sh
set -e

if [ -z "${TOOL_INPUT_TARGET}" ]; then
  echo '{"success":false,"output":null,"facts":[],"error":"TOOL_INPUT_TARGET is required"}' >&1
  exit 2
fi

# 解析可選參數
PORTS=$(echo "${TOOL_INPUT_PARAMS:-{}}" | jq -r '.ports // "1-1000"')
SCAN_TYPE=$(echo "${TOOL_INPUT_PARAMS:-{}}" | jq -r '.scan_type // "syn"')

# 支援批次輸入（擴展層）
TARGET_ARG="${TOOL_INPUT_TARGET}"
if [ -n "${TOOL_INPUT_FILE}" ] && [ -f "${TOOL_INPUT_FILE}" ]; then
  TARGET_ARG="-iL ${TOOL_INPUT_FILE}"
fi

# 執行 nmap，XML 報告寫入 /output/（擴展層）
mkdir -p /output
nmap -s"${SCAN_TYPE}" -p "${PORTS}" -oX /output/scan-report.xml ${TARGET_ARG} >/dev/null 2>&1 || {
  echo '{"success":false,"output":null,"facts":[],"error":"nmap scan failed"}' >&1
  exit 1
}

# 從 XML 擷取 facts (基礎層) + 生成 manifest (擴展層)
python3 -c "
import xml.etree.ElementTree as ET, json, sys, os

tree = ET.parse('/output/scan-report.xml')
facts = []
output_lines = []

for host in tree.findall('.//host'):
    addr = host.find('address')
    if addr is None:
        continue
    ip = addr.get('addr', '')
    facts.append({'trait': 'network.host.ip', 'value': ip})

    os_match = host.find('.//osmatch')
    if os_match is not None:
        facts.append({'trait': 'host.os', 'value': os_match.get('name', '')})

    for port in host.findall('.//port'):
        proto = port.get('protocol', 'tcp')
        portid = port.get('portid', '')
        state = port.find('state')
        if state is not None and state.get('state') == 'open':
            svc = port.find('service')
            svc_name = svc.get('name', '') if svc is not None else ''
            facts.append({'trait': 'service.port', 'value': f'{ip}:{portid}/{svc_name}'})

            product = svc.get('product', '') if svc is not None else ''
            version = svc.get('version', '') if svc is not None else ''
            if product:
                banner = f'{product} {version}'.strip()
                facts.append({'trait': 'service.banner', 'value': banner})
            output_lines.append(f'{portid}/{proto} open {svc_name}')

# --- 基礎層：stdout JSON ---
result = {
    'success': True,
    'output': f'Nmap scan of {sys.argv[1]}: {len(output_lines)} open ports found',
    'facts': facts,
    'error': None
}
json.dump(result, sys.stdout)

# --- 擴展層：manifest.json ---
xml_size = os.path.getsize('/output/scan-report.xml')
manifest = {
    'artifacts': [
        {
            'name': 'scan-report.xml',
            'path': 'scan-report.xml',
            'media_type': 'application/xml',
            'size_bytes': xml_size,
            'description': f'Nmap full scan report for {sys.argv[1]}',
            'category': 'report'
        }
    ]
}
with open('/output/manifest.json', 'w') as f:
    json.dump(manifest, f)
" "${TOOL_INPUT_TARGET}"
```

**stdout 輸出（基礎層 — facts）：**
```json
{
  "success": true,
  "output": "Nmap scan of 10.0.1.5: 3 open ports found",
  "facts": [
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "host.os", "value": "Windows Server 2019"},
    {"trait": "service.port", "value": "10.0.1.5:445/microsoft-ds"},
    {"trait": "service.banner", "value": "Microsoft Windows RPC"},
    {"trait": "service.port", "value": "10.0.1.5:3389/ms-wbt-server"},
    {"trait": "service.port", "value": "10.0.1.5:88/kerberos-sec"}
  ],
  "error": null
}
```

**/output/ 內容（擴展層 — artifact）：**
```
/output/
├── manifest.json       # 產物清單
└── scan-report.xml     # 完整 nmap XML（45KB，遠超 facts 的 500 字元限制）
```

### 範例 3：gobuster（目錄列舉 — 使用 /input/ 擴展層輸入）

展示需要 wordlist 檔案輸入的工具。

```bash
#!/bin/sh
set -e

if [ -z "${TOOL_INPUT_TARGET}" ]; then
  echo '{"success":false,"output":null,"facts":[],"error":"TOOL_INPUT_TARGET is required"}' >&1
  exit 2
fi

# 字典檔來源：/input/ 掛載 > 容器內建 > 預設
WORDLIST="${TOOL_INPUT_WORDLIST:-/input/wordlists/common.txt}"
if [ ! -f "${WORDLIST}" ]; then
  WORDLIST="/usr/share/wordlists/dirb/common.txt"  # 容器內建 fallback
fi

RESULT=$(gobuster dir -u "${TOOL_INPUT_TARGET}" -w "${WORDLIST}" -q 2>/dev/null) || {
  echo '{"success":false,"output":null,"facts":[],"error":"gobuster failed"}' >&1
  exit 1
}

echo "${RESULT}" | jq -Rsc --arg target "${TOOL_INPUT_TARGET}" '{
  success: true,
  output: ("Directory enumeration for " + $target + ": found " + (split("\n") | map(select(length > 0)) | length | tostring) + " paths"),
  facts: [split("\n")[] | select(length > 0) | {trait: "service.url", value: ($target + "/" + .)}],
  error: null
}'
```

**ContainerEngineClient 呼叫方式：**
```
docker run --rm \
  -e TOOL_INPUT_TARGET=https://example.com \
  -e TOOL_INPUT_WORDLIST=/input/wordlists/big.txt \
  -v /athena/wordlists:/input/wordlists:ro \
  athena-tools/gobuster:1.0
```

---

## ContainerEngineClient 執行流程

```
1. 從 registry.yaml 查找工具定義
2. 準備 volume mounts：
   a. 建立臨時 output 目錄 → 掛載為 /output
   b. 若 params 含 input_files → 掛載為 /input（唯讀）
   c. 若有前步產出需串接 → 掛載至 /input/previous
3. 設定環境變數：
   - TOOL_INPUT_TARGET = target
   - TOOL_INPUT_ABILITY_ID = ability_id
   - TOOL_EXECUTION_ID = execution_id
   - TOOL_INPUT_PARAMS = json.dumps(params) if params else "{}"
   - TOOL_TIMEOUT = registry.timeout
   - TOOL_INPUT_FILE = /input/targets.txt (若有批次輸入)
   - TOOL_INPUT_WORDLIST = /input/wordlists/... (若需字典)
4. docker run --rm --network=host \
     -e TOOL_INPUT_TARGET=... \
     -e ... \
     -v {output_dir}:/output \
     -v {input_dir}:/input:ro \
     {image}
5. 等待容器結束（最多 timeout 秒）
6. 解析 stdout JSON → ExecutionResult (基礎層)
7. 若 /output/manifest.json 存在：
   a. 解析 manifest → ExecutionArtifact 列表
   b. 將產物從臨時目錄移至持久化儲存
   c. 附加至 ExecutionResult.artifacts
8. 若 exit code 非 0 且無有效 JSON → 生成 error ExecutionResult
9. 回傳 ExecutionResult 給 EngineRouter
10. 清理臨時目錄
```

---

## 驗收標準（Acceptance Criteria）

### 基礎層

| # | 標準 | 驗證方式 |
|---|------|----------|
| 1 | 符合規格的容器 JSON 輸出可被 `json.loads()` 解析 | 單元測試 |
| 2 | 輸出 facts 的 trait 可被 `_category_from_trait()` 正確分類 | 單元測試 |
| 3 | Exit code 0 時 `success=true`，exit code 1 時 `success=false` | 整合測試 |
| 4 | 缺少 `TOOL_INPUT_TARGET` 時回傳 exit 2 + error JSON | 整合測試 |
| 5 | 超過 timeout 時 `ContainerEngineClient` 回傳 timeout error | 整合測試 |
| 6 | 工具 log 只寫 stderr，不污染 stdout JSON | 手動驗證 |
| 7 | Registry YAML 中每個工具的 `output.traits` 匹配實際輸出 | 整合測試 |

### 擴展層（/input/ + /output/）

| # | 標準 | 驗證方式 |
|---|------|----------|
| 8 | `/input/` 掛載的檔案在容器內可讀取 | 整合測試 |
| 9 | 需要 wordlist 的工具在 `/input/wordlists/` 不存在時 fallback 至內建字典 | 整合測試 |
| 10 | `/output/manifest.json` 可被 `json.loads()` 解析且符合 schema | 單元測試 |
| 11 | `manifest.json` 中每個 artifact 的 `path` 指向實際存在的檔案 | 整合測試 |
| 12 | `manifest.json` 中的 `size_bytes` 與實際檔案大小一致 | 整合測試 |
| 13 | 不產出 artifact 的工具可正常運行（無 `/output/manifest.json`） | 整合測試 |
| 14 | 前步工具的 `/output/` 產物可掛載為後步工具的 `/input/previous/` | 整合測試 |

<!-- tech-debt: scenario-pending — v3.2 upgrade: needs test matrix + Gherkin scenarios -->
<!-- tech-debt: observability-pending — v3.3 upgrade: needs observability section -->
