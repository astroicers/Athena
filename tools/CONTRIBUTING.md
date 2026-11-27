# Contributing to athena-tools

發布一個 MCP 工具，讓 Athena 自動調度它。合併需簽 **CLA**。

## 貢獻流程

1. **發布**：PR 你的工具包到 `catalog/<container>/`——容器層放 `Dockerfile` + `server.py`，每個 FastMCP `tool_name` 一份 `<tool_name>.athena-tool.toml`（單工具容器就一份）。
2. **審核**：維護者 review manifest 與容器（信任閘）；合併需簽 CLA。
3. **部署**：operator 在自己的 Athena 部署 opt-in 選要載入哪些工具（執行信任閘）。
4. **調度**：Athena 從 manifest 資料驅動載入 → ORIENT 自動發現，**未改核心**。

## Manifest 規則

- 依 [`schema/athena-tool.schema.json`](schema/athena-tool.schema.json) 撰寫 manifest（CI 會驗）。
- 檔案格式統一 **`.toml`**，檔名 **`<tool_name>.athena-tool.toml`**。
- **佈局**：`catalog/<container>/<tool_name>.athena-tool.toml`；目錄名 == manifest 的 `container` 欄位，一個 `tool_name` 一份檔（多工具容器＝同目錄多份 manifest，共用一份 `Dockerfile`/`server.py`）。CI 另驗 `container` 欄位與目錄名一致、且 `tool_name` 在整個 catalog 唯一。
- **Phase 1：外部工具限 targetless**（OSINT / 查詢類）。需 victim IP 注入的工具（`target_param`）為 Phase 2。
- `techniques` 必須是真實 MITRE ATT&CK ID，且如實描述工具。
- `sensitive = true` 的工具走 gated/私有目錄，不進公開 catalog。

## CLA

> **目前暫不接受外部貢獻的合併。** 本專案採 CLA（DCO 不足以轉讓將貢獻併入 BSL 核心所需之權利）；CLA 全文與法定受讓實體將於開放貢獻前正式發布。歡迎以 issue 交流。

## 授權使用限制

本 catalog 及其工具僅供**授權**用途。見 [SECURITY.md](SECURITY.md) 與 [Athena 使用限制](https://github.com/astroicers/Athena#授權與使用限制)。

## 行為準則

見 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
