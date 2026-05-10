# [ADR-116]: 24 MCP Tool Containers on k3s

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

v1.x 的 24 個 MCP 工具容器透過 `docker-compose.yml` 管理。2.0 目標是將所有工作負載遷移到 k3s。

## 決策

- 每個 MCP 工具容器對應一個 k3s `Deployment` + `ClusterIP Service`
- Helm chart 在 `deploy/helm/athena/templates/mcp/` 以 `range .Values.mcp.tools` 動態產生
- 容器映像不變（UNCHANGED from v1）；只變更部署方式
- MCP client 的 `base_url` 由 `AthenaConfig.mcp.base_url` 控制，k3s 環境改為 ClusterIP DNS

## 後果

- `docker-compose.yml` 繼續保留作本地開發用
- k3s 生產環境透過 Helm values 設定工具清單

## 關聯

- 依賴：ADR-115（k3s 基礎架構）
