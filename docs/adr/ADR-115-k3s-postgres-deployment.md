# [ADR-115]: k3s PostgreSQL Deployment + Helm Chart Skeleton

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

Athena 2.0 需要 PostgreSQL 作為持久化層。開發環境使用 k3s（192.168.0.27:30543），生產部署採用 Helm chart。

## 決策

- PostgreSQL 透過 k3s `Deployment` + `NodePort Service`（30543）部署
- Helm chart skeleton 位於 `deploy/helm/athena/`，結構遵循 Helm v3 最佳實踐
- `athena-workspace` 二進位以 Deployment 部署，ConfigMap 掛載 `athena.toml`
- Secrets（DB 密碼、API Key）透過 k3s Secret 注入，不進 Git

## 後果

- `athena.toml` 不 commit（已 gitignore），改由 Helm values 管理
- 資料庫 schema 由 `sqlx migrate run` 在 Job 中執行（migrations 在 `crates/athena-db/migrations/`）

## 關聯

- 依賴：ADR-111（sqlx）、ADR-108（constructor injection）
