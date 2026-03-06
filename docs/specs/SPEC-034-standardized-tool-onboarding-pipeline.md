# SPEC-034：Standardized Tool Onboarding Pipeline

> 讓新 MCP 工具的加入從 5 步手動操作縮減為 `make new-tool` 一鍵完成，開發者只需專注 `server.py` 實作與 `tool.yaml` metadata。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-034 |
| **關聯 ADR** | ADR-030（Standardized Tool Onboarding Pipeline）、ADR-024（MCP Architecture） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 標準化新 MCP 工具的加入流程：`make new-tool NAME=xxx` 一鍵完成 scaffold + 自動註冊（`mcp_servers.json`、`docker-compose.yml`），搭配 `tool.yaml` 作為工具 metadata 的 single source of truth，並提供 `make dev-tool` 本地開發流程。解決開發者需手動編輯 4 個分散設定檔、template 與 production 不一致的問題。

---

## 📥 輸入規格（Inputs）

### `make new-tool NAME=<tool-name>`

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `NAME` | string | Makefile 變數 | slug 格式（小寫字母 + 連字號），例：`dns-enum`、`web-crawler` |

### `make dev-tool NAME=<tool-name>`

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `NAME` | string | Makefile 變數 | 必須對應 `tools/<NAME>/` 已存在的目錄 |

### `make dev-tool-http NAME=<tool-name> [PORT=<port>]`

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| `NAME` | string | Makefile 變數 | 必須對應 `tools/<NAME>/` 已存在的目錄 |
| `PORT` | int | Makefile 變數（可選） | 預設 8090，範圍 1024-65535 |

---

## 📤 輸出規格（Expected Output）

### `make new-tool NAME=dns-enum` 成功輸出

```
✅ MCP tool scaffold created: tools/dns-enum/
   Created:
   - tools/dns-enum/server.py
   - tools/dns-enum/Dockerfile
   - tools/dns-enum/pyproject.toml
   - tools/dns-enum/tool.yaml
   - tools/dns-enum/README.md
   Registered:
   - mcp_servers.json → added "dns-enum" server entry
   - docker-compose.yml → added "mcp-dns-enum" service (port 58096)
   Next steps:
   1. Edit tools/dns-enum/server.py — implement your tool logic
   2. Edit tools/dns-enum/tool.yaml — fill in metadata (MITRE, traits, etc.)
   3. make dev-tool NAME=dns-enum — test locally
   4. make build-mcp — build Docker images
```

### `make new-tool NAME=dns-enum` 重複執行（冪等保護）

```
❌ Tool 'dns-enum' already exists at tools/dns-enum/
   Use 'make remove-tool NAME=dns-enum' to remove it first.
```

---

## 📂 產出物件規格

### 1. `tools/_template/tool.yaml`（模板）

```yaml
# Athena MCP Tool Metadata
# 此檔案是工具 metadata 的 single source of truth
# scaffold_tool.py 會讀取此檔案自動註冊 mcp_servers.json 和 docker-compose.yml

tool_id: "{{TOOL_NAME}}"
name: "{{TOOL_NAME}}"
description: "TODO: describe what this tool does"
category: "reconnaissance"         # reconnaissance | credential_access | execution | lateral_movement | collection
risk_level: "low"                  # low | medium | high | critical
mitre_techniques: []               # e.g. ["T1046", "T1595.002"]
output_traits: []                  # e.g. ["network.host.ip", "service.open_port"]

# MCP Server Config（自動注入 mcp_servers.json）
mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-{{TOOL_NAME}}:8080/mcp"
  tool_prefix: "{{TOOL_NAME}}"

# Docker Compose Config（自動注入 docker-compose.yml）
docker:
  port: 0                          # 0 = auto-assign next available 5809x port
  environment: {}                  # extra env vars, e.g. {NVD_API_KEY: "${NVD_API_KEY:-}"}
```

### 2. `tools/_template/server.py`（升級版模板）

```python
"""{{TOOL_NAME}} MCP Server for Athena.

Exposes tools via the Model Context Protocol.
Each tool SHOULD return JSON with {"facts": [{"trait": ..., "value": ...}]}
to integrate with Athena's fact collection pipeline.
"""

import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Allow Docker internal network hostnames (mcp-xxx, etc.)
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP("athena-{{TOOL_NAME}}", transport_security=_security)


@mcp.tool()
async def example_scan(target: str) -> str:
    """Example tool: scan a target and return facts.

    Args:
        target: IP address or hostname to scan.

    Returns:
        JSON string with Athena-compatible facts.
    """
    # TODO: Replace with real implementation
    facts = [
        {"trait": "network.host.ip", "value": target},
    ]
    return json.dumps({"facts": facts, "raw_output": f"Scanned {target}"})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport", default="stdio",
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
```

### 3. `tools/_template/README.md`（升級版）

```markdown
# {{TOOL_NAME}} — Athena MCP Tool Server

## Quick Start

### 1. Scaffold (already done)
\`\`\`bash
make new-tool NAME={{TOOL_NAME}}
\`\`\`

### 2. Implement tool logic
Edit `server.py` — replace `example_scan` with your tool function(s).

**Output convention:** Return JSON string with Athena-compatible facts:
\`\`\`json
{
  "facts": [
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "host.os", "value": "Linux"}
  ],
  "raw_output": "Human-readable scan output..."
}
\`\`\`

### 3. Fill in metadata
Edit `tool.yaml` — set description, category, mitre_techniques, output_traits.

### 4. Test locally
\`\`\`bash
make dev-tool NAME={{TOOL_NAME}}           # stdio mode
make dev-tool-http NAME={{TOOL_NAME}}      # HTTP mode (port 8090)
\`\`\`

### 5. Build & Deploy
\`\`\`bash
make build-mcp
docker compose --profile mcp up -d
\`\`\`

MCPClientManager will auto-discover tools and sync to tool_registry DB.

## Dependencies

Add Python dependencies to `pyproject.toml` under `[project] dependencies`.

If system packages are needed (e.g. nmap), add them to `Dockerfile`:
\`\`\`dockerfile
FROM athena-mcp-base:latest
RUN apt-get update && apt-get install -y --no-install-recommends <package> && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
CMD ["python", "-m", "server"]
\`\`\`
```

### 4. `scripts/scaffold_tool.py`

**功能**：自動化 scaffold + 註冊腳本

**輸入**：`tool_name`（位置參數，slug 格式）

**執行邏輯**：

```
def main(tool_name: str):
    project_root = detect_project_root()    # 找到 mcp_servers.json 所在目錄
    tool_dir = project_root / "tools" / tool_name

    # Step 1: 檢查是否已存在
    if tool_dir.exists():
        print(f"❌ Tool '{tool_name}' already exists at {tool_dir}")
        sys.exit(1)

    # Step 2: 複製 template
    template_dir = project_root / "tools" / "_template"
    shutil.copytree(template_dir, tool_dir)

    # Step 3: 替換 {{TOOL_NAME}}
    for file in tool_dir.rglob("*"):
        if file.is_file() and file.suffix in (".py", ".toml", ".yaml", ".md"):
            text = file.read_text()
            file.write_text(text.replace("{{TOOL_NAME}}", tool_name))

    # Step 4: 注入 mcp_servers.json
    mcp_file = project_root / "mcp_servers.json"
    mcp_data = json.loads(mcp_file.read_text())
    if tool_name not in mcp_data["servers"]:
        tool_yaml = yaml.safe_load((tool_dir / "tool.yaml").read_text())
        mcp_cfg = tool_yaml["mcp"]
        mcp_data["servers"][tool_name] = {
            "transport": mcp_cfg["transport"],
            "command": mcp_cfg["command"],
            "args": mcp_cfg["args"],
            "env": {},
            "http_url": mcp_cfg["http_url"],
            "enabled": True,
            "description": tool_yaml.get("description", ""),
            "tool_prefix": mcp_cfg.get("tool_prefix", tool_name),
        }
        mcp_file.write_text(json.dumps(mcp_data, indent=2) + "\n")
        print(f"   ✅ mcp_servers.json → added '{tool_name}'")
    else:
        print(f"   ⏭  mcp_servers.json → '{tool_name}' already exists, skipped")

    # Step 5: 注入 docker-compose.yml
    compose_file = project_root / "docker-compose.yml"
    compose_text = compose_file.read_text()
    service_name = f"mcp-{tool_name}"
    if service_name not in compose_text:
        next_port = find_next_port(compose_text)   # 掃描 5809x 模式
        service_block = generate_service_block(tool_name, next_port, tool_yaml)
        # 在 volumes: 區塊前插入新 service
        compose_text = insert_before_volumes(compose_text, service_block)
        compose_file.write_text(compose_text)
        print(f"   ✅ docker-compose.yml → added '{service_name}' (port {next_port})")
    else:
        print(f"   ⏭  docker-compose.yml → '{service_name}' already exists, skipped")
```

**Port 自動分配邏輯**：
```python
def find_next_port(compose_text: str) -> int:
    """掃描 docker-compose.yml 找出所有 5809x port，回傳下一個可用。"""
    import re
    ports = re.findall(r"58(\d{3}):8080", compose_text)
    used = {int(f"58{p}") for p in ports}
    candidate = 58091
    while candidate in used:
        candidate += 1
    return candidate
```

**Service block 生成**：
```python
def generate_service_block(tool_name: str, port: int, tool_yaml: dict) -> str:
    env_lines = ""
    docker_env = tool_yaml.get("docker", {}).get("environment", {})
    if docker_env:
        env_lines = "\n    environment:\n"
        for k, v in docker_env.items():
            env_lines += f"      - {k}={v}\n"

    return f"""
  mcp-{tool_name}:
    build: {{ context: ./tools/{tool_name} }}
    profiles: [mcp]
    command: ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
{env_lines}    ports:
      - "127.0.0.1:{port}:8080"
    restart: unless-stopped
"""
```

**依賴**：Python 標準庫 + `PyYAML`（已在 backend requirements 中）

### 5. Makefile 變更

**修改檔案：** `Makefile`

```makefile
#---------------------------------------------------------------------------
# MCP Tool Scaffolding
#---------------------------------------------------------------------------

new-tool:  ## 建立新的 MCP tool server（用法: make new-tool NAME=my-scanner）
	@if [ -z "$(NAME)" ]; then echo "Usage: make new-tool NAME=my-scanner"; exit 1; fi
	@python3 scripts/scaffold_tool.py $(NAME)

dev-tool:  ## 本地 stdio 模式啟動 MCP tool（用法: make dev-tool NAME=my-scanner）
	@if [ -z "$(NAME)" ]; then echo "Usage: make dev-tool NAME=my-scanner"; exit 1; fi
	@if [ ! -d "tools/$(NAME)" ]; then echo "❌ tools/$(NAME)/ not found"; exit 1; fi
	cd tools/$(NAME) && pip install -q -e . 2>/dev/null; python -m server

dev-tool-http:  ## 本地 HTTP 模式啟動 MCP tool（用法: make dev-tool-http NAME=my-scanner [PORT=8090]）
	@if [ -z "$(NAME)" ]; then echo "Usage: make dev-tool-http NAME=my-scanner"; exit 1; fi
	@if [ ! -d "tools/$(NAME)" ]; then echo "❌ tools/$(NAME)/ not found"; exit 1; fi
	cd tools/$(NAME) && pip install -q -e . 2>/dev/null; python -m server --transport streamable-http --port $(or $(PORT),8090)
```

### 6. 現有工具回填 `tool.yaml`

為 5 個現有工具建立 `tool.yaml`，metadata 來源：`mcp_servers.json` + `docker-compose.yml` + 各 `server.py` 分析。

#### `tools/nmap-scanner/tool.yaml`

```yaml
tool_id: "nmap-scanner"
name: "Nmap Scanner"
description: "Nmap port scanner and service detection"
category: "reconnaissance"
risk_level: "medium"
mitre_techniques: ["T1046"]
output_traits: ["service.open_port", "network.host.ip", "host.os"]

mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-nmap:8080/mcp"
  tool_prefix: "nmap"

docker:
  port: 58091
  environment: {}
```

#### `tools/osint-recon/tool.yaml`

```yaml
tool_id: "osint-recon"
name: "OSINT Recon"
description: "OSINT subdomain enumeration and DNS resolution"
category: "reconnaissance"
risk_level: "low"
mitre_techniques: ["T1595.002", "T1596"]
output_traits: ["network.subdomain", "network.host.ip"]

mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-osint:8080/mcp"
  tool_prefix: "osint"

docker:
  port: 58092
  environment: {}
```

#### `tools/vuln-lookup/tool.yaml`

```yaml
tool_id: "vuln-lookup"
name: "Vulnerability Lookup"
description: "CVE lookup via NVD API with CPE mapping"
category: "reconnaissance"
risk_level: "low"
mitre_techniques: ["T1592"]
output_traits: ["vuln.cve", "vuln.severity"]

mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-vuln:8080/mcp"
  tool_prefix: "vuln"

docker:
  port: 58093
  environment:
    NVD_API_KEY: "${NVD_API_KEY:-}"
```

#### `tools/credential-checker/tool.yaml`

```yaml
tool_id: "credential-checker"
name: "Credential Checker"
description: "SSH, RDP, and WinRM credential testing"
category: "credential_access"
risk_level: "high"
mitre_techniques: ["T1110", "T1110.001"]
output_traits: ["credential.ssh", "credential.rdp", "credential.winrm"]

mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-credential-checker:8080/mcp"
  tool_prefix: "cred"

docker:
  port: 58094
  environment: {}
```

#### `tools/attack-executor/tool.yaml`

```yaml
tool_id: "attack-executor"
name: "Attack Executor"
description: "Post-compromise SSH/WinRM technique execution"
category: "execution"
risk_level: "critical"
mitre_techniques: ["T1059", "T1059.004"]
output_traits: ["execution.result", "file.content", "host.user.name"]

mcp:
  transport: "stdio"
  command: "python"
  args: ["-m", "server"]
  http_url: "http://mcp-attack-executor:8080/mcp"
  tool_prefix: "attack"

docker:
  port: 58095
  environment:
    SESSION_IDLE_TIMEOUT_SEC: "300"
```

---

## 🔗 副作用與連動（Side Effects）

| 本功能的狀態變動 | 受影響的既有功能 | 預期行為 |
|-----------------|----------------|---------|
| `mcp_servers.json` 新增 entry | `MCPClientManager.startup()` | 下次啟動時自動連線新工具伺服器、發現並同步工具至 `tool_registry` |
| `docker-compose.yml` 新增 service | `docker compose --profile mcp up` | 新工具容器隨 MCP profile 啟動 |
| `tools/_template/server.py` 變更 | 已存在的 5 個工具 | **無影響** — template 變更只影響新建工具，現有工具各自有獨立 `server.py` |
| 現有工具新增 `tool.yaml` | 無 | `tool.yaml` 為純 metadata 檔案，不被任何運行時組件讀取（僅供 scaffold 腳本使用） |
| `Makefile` `new-tool` target 變更 | 已使用 `make new-tool` 的開發者 | 行為增強（自動註冊），不破壞現有用法 |

---

## ⚠️ 邊界條件（Edge Cases）

- **Case 1**：`make new-tool NAME=nmap-scanner`（已存在的工具名稱）→ 報錯退出，不覆蓋
- **Case 2**：`make new-tool NAME=my_tool`（含底線）→ 可接受，但建議 slug 用連字號。腳本不強制，只印提示
- **Case 3**：`mcp_servers.json` 已有同名 entry 但 `tools/<name>/` 不存在（手動殘留）→ 腳本建立目錄但跳過 JSON 注入
- **Case 4**：`docker-compose.yml` 格式被手動破壞 → 腳本使用字串插入而非 YAML 解析，對格式容錯
- **Case 5**：所有 `5809x` port 已用完（58091-58099 共 9 個）→ 腳本跳到 58100 繼續分配
- **Case 6**：`make dev-tool NAME=xxx` 但 `tools/xxx/` 不存在 → 報錯退出
- **Case 7**：`PyYAML` 未安裝 → 腳本在 import 時報錯，提示 `pip install pyyaml`

### 回退方案（Rollback Plan）

- **回退方式**：`git revert` commit 即可完整回退。所有變更為新增檔案或追加內容，不修改現有運行時邏輯
- **不可逆評估**：無不可逆操作。template 變更不影響已建立的工具目錄
- **資料影響**：無。`tool.yaml` 為純 metadata，不影響 DB 或運行時狀態

---

## ✅ 驗收標準（Done When）

- [ ] `make new-tool NAME=test-dummy` 成功建立 `tools/test-dummy/`，含 `server.py`、`Dockerfile`、`pyproject.toml`、`tool.yaml`、`README.md`
- [ ] `tools/test-dummy/server.py` 包含 `TransportSecuritySettings` 和 `argparse` 區塊
- [ ] `mcp_servers.json` 自動新增 `"test-dummy"` entry，格式與現有 5 個 entry 一致
- [ ] `docker-compose.yml` 自動新增 `mcp-test-dummy` service，port 為 `58096`（下一個可用），profile 為 `[mcp]`
- [ ] 再次執行 `make new-tool NAME=test-dummy` 報錯提示已存在，不重複操作
- [ ] `make dev-tool NAME=test-dummy` 在本地 stdio 模式正常啟動（可用 Ctrl+C 退出）
- [ ] `make dev-tool-http NAME=test-dummy` 在本地 HTTP 模式正常啟動（port 8090）
- [ ] 5 個現有工具各有 `tool.yaml`，metadata 與 `mcp_servers.json` / `docker-compose.yml` 一致
- [ ] `make build-mcp` 全部工具（含現有 5 個）build 成功，無回歸
- [ ] 清理測試：`rm -rf tools/test-dummy` + 手動移除 JSON/YAML entries 後狀態乾淨
- [ ] `make lint` 無 error（若適用）

---

## 🚫 禁止事項（Out of Scope）

- **不修改**：`backend/app/services/mcp_client_manager.py`、`engine_router.py`、`mcp_fact_extractor.py`（運行時邏輯不變）
- **不修改**：現有 5 個工具的 `server.py`（只新增 `tool.yaml`）
- **不引入新的運行時依賴**：`scaffold_tool.py` 僅在開發時執行，使用 `PyYAML`（已存在）+ 標準庫
- **不實作**：`make remove-tool` — 可作為後續 enhancement
- **不實作**：`tool.yaml` 的 CI lint / JSON schema 驗證 — 可作為後續 enhancement
- **不實作**：基於 `tool.yaml` 的運行時 seed（目前 tool_registry seed 由 `database.py` 管理，不改動）

---

## 📂 影響檔案

### 新增

| 檔案 | 說明 |
|------|------|
| `scripts/scaffold_tool.py` | 自動化 scaffold + 註冊腳本（~150 行） |
| `tools/_template/tool.yaml` | 工具 metadata 模板 |
| `tools/nmap-scanner/tool.yaml` | 回填 metadata |
| `tools/osint-recon/tool.yaml` | 回填 metadata |
| `tools/vuln-lookup/tool.yaml` | 回填 metadata |
| `tools/credential-checker/tool.yaml` | 回填 metadata |
| `tools/attack-executor/tool.yaml` | 回填 metadata |

### 修改

| 檔案 | 改動摘要 |
|------|----------|
| `tools/_template/server.py` | 加入 `TransportSecuritySettings` + `argparse` 區塊 |
| `tools/_template/README.md` | 升級為完整 5 步驟流程 |
| `Makefile` | `new-tool` 改呼叫 `scaffold_tool.py`；新增 `dev-tool`、`dev-tool-http` targets |

### 不修改（運行時組件）

| 檔案 | 理由 |
|------|------|
| `backend/app/services/mcp_client_manager.py` | 自動發現機制不變 |
| `backend/app/services/mcp_fact_extractor.py` | fact 解析邏輯不變 |
| `backend/app/routers/tools.py` | CRUD API 不變 |
| `backend/app/database.py` | seed 邏輯不變 |
| `mcp_servers.json` | 由 scaffold 腳本自動修改，非手動 |
| `docker-compose.yml` | 由 scaffold 腳本自動修改，非手動 |

---

## 📎 參考資料（References）

- 相關 ADR：[ADR-030](../adr/ADR-030-standardized-tool-onboarding-pipeline.md)、[ADR-024](../adr/ADR-024-mcp-architecture-and-tool-server-integration.md)
- 現有類似實作：[SPEC-016](SPEC-016-tool-container-io-standard.md)（Container I/O Standard）、[SPEC-025](SPEC-025-tool-registry-management.md)（Tool Registry Management）
- 現有 template：`tools/_template/`
- Production 參考：`tools/nmap-scanner/server.py`（含 argparse + TransportSecuritySettings 的完整範例）
