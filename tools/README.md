```
 █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗
██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗
███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║
██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║
██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║
╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
   T O O L S  ·  data-driven MCP tool catalog
```

# athena-tools

[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-roadmap-orange.svg)](#狀態)

> **Athena 的工具 catalog** — 發布一個 MCP 工具，讓 [Athena](https://github.com/astroicers/Athena) 的自主 OODA 迴圈**自動調度它**，而且**加工具不改核心**。

`athena-tools` 收錄社群工具包（容器 + Athena manifest）。任何人可發布工具、operator 選擇部署——Athena 核心從 manifest **資料驅動載入** registry，無需改核心源碼、無需 rebuild。

> ⚠️ **授權使用限制**：Athena 及其工具僅供你**擁有**或已取得**書面授權**的系統（授權紅隊 / CTF / 靶場 / 學術 / 教育）。嚴禁未經授權使用。使用者自負法律責任。見 [SECURITY.md](SECURITY.md)。
>
> 🗺️ **狀態：規劃中（roadmap）。** 資料驅動 registry 與 manifest 機制已定案。

---

## 生態系

| 專案 | 是什麼 | 可見度 · 授權 |
|------|--------|--------------|
| [**Athena**](https://github.com/astroicers/Athena) | 產品門面 · 開源入口 | 🌐 公開 |
| **athena-sdk** *(規劃中)* | 模組契約 trait | 🌐 Apache-2.0 |
| **athena-tools**（本 repo） | 工具 catalog | 🌐 Apache-2.0 |
| **athena-core** | 自主 OODA 商業引擎 · 洽談取得 | 🔒 BSL 1.1 |

---

## 一個工具包長怎樣

```
my-tool/
├── athena-tool.toml     # Athena manifest（讓核心認得這個工具）
├── Dockerfile           # MCP 工具容器（FastMCP · streamable-http · EXPOSE 8080）
└── server.py            # @mcp.tool() 實作，回 {"facts": [...]}
```

`athena-tool.toml`（manifest，見 [`examples/my-tool/`](examples/my-tool/)）：

```toml
manifest_version = "1"
tool_name   = "example_query"
container   = "example-osint"
port        = 9130
techniques  = ["T1596"]          # MITRE ATT&CK；核心據此把工具塞進 ORIENT 可用清單
phase       = "observe"          # observe | act | both
os_hint     = "any"
params_hint = "domain=<name>"    # 餵給 LLM 的填參提示
sensitive   = false              # true → 走 gated/私有目錄，不進公開 catalog
```

> ℹ️ **Phase 1：外部工具目前限 targetless**（OSINT / 查詢類，如上例）。需要把 victim IP 注入工具參數的工具（scope-target 資料化，`target_param`）為 **Phase 2**。
>
> manifest 檔統一 **`.toml`**；`schema/athena-tool.schema.json` 供貢獻期驗證（JSON-Schema）。

---

## Catalog 佈局（多工具容器）

收錄的工具放在 [`catalog/`](catalog/)，**一個容器一個目錄**；容器碼（`Dockerfile` / `server.py`）在容器層，每個 FastMCP `tool_name` 一份 manifest：

```
catalog/
└── <container>/                       # 目錄名 == manifest 的 container 欄位
    ├── Dockerfile
    ├── server.py
    ├── <tool_a>.athena-tool.toml
    └── <tool_b>.athena-tool.toml
```

哪些容器收進本**公開** catalog，由 [`catalog/allowlist.toml`](catalog/allowlist.toml) 界定（可公開的治理清單）。

operator 部署時把要載入的**容器目錄**（如 `catalog/osint`）逐一列進 Athena 的 `tool_manifest_dirs`（opt-in，一容器一筆），ORIENT 即自動發現該容器的所有工具——**加工具不改核心**。

> ℹ️ 本 catalog 為**公開發布**：社群工具、或核心未內建的工具變體。若某工具名與官方 Athena **已內建**的同名，官方核心會以 builtin 優先、跳過該 manifest（fail-closed + loud log）——此為設計預期；catalog **不是**用來讓官方核心「熱載自己已內建的工具」。

---

## Build / Test / Run（範例工具）

從範例工具包 `examples/my-tool/` 就能驗 manifest、建容器、本地起服務：

```bash
cd examples/my-tool

# 1) 驗證 manifest 符合 schema
pip install check-jsonschema
python -c "import tomllib,json; json.dump(tomllib.load(open('athena-tool.toml','rb')), open('/tmp/m.json','w'))"
check-jsonschema --schemafile ../../schema/athena-tool.schema.json /tmp/m.json

# 2) 建工具容器（FastMCP · streamable-http）
docker build -t my-scanner .

# 3) 本地起工具（:8080）
docker run --rm -p 8080:8080 my-scanner
```

工具起來後，operator 在 Athena 部署把它列入 `tool_manifest_dirs`（opt-in），ORIENT 即自動發現／調度——**加工具不改核心**。

## 貢獻流程

1. **發布**：PR 你的工具包（容器 + `athena-tool.toml`）進本 catalog。
2. **審核**：維護者 review manifest 與容器（信任閘）；合併需簽 **CLA**。
3. **部署**：operator 在自己的 Athena 部署中 opt-in 選要載入哪些工具（執行信任閘）。
4. **調度**：Athena 從 manifest 資料驅動載入 → ORIENT 自動發現/選用，**未改核心**。

詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

> 壞/惡意 manifest 只會被載入時跳過（fail-closed + loud log），且工具的任何動作仍受 Athena 的 scope / opsec / policy 硬閘界定——**資料驅動不弱化安全**。

## 授權

Apache License 2.0 — 見 [LICENSE](LICENSE)。工具容器內第三方工具（nmap / nikto / ffuf / dnsutils / whois / gh …）各自尊重其上游授權。
