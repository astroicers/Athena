# [ADR-117]: Argo CD GitOps Configuration

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

需要宣告式 GitOps 管理 k3s 工作負載，確保 Git 為唯一真相來源。

## 決策

- Argo CD Application 資源位於 `deploy/argocd/`
- `syncPolicy.automated` 啟用（prune + self-heal）
- Helm chart 為 source，values 覆寫由 `deploy/argocd/athena-app.yaml` 管理
- 映像版本透過 Argo CD Image Updater（2.1）自動更新

## 後果

- 所有 k3s 狀態變更透過 Git PR，禁止直接 `kubectl apply` 生產環境
- 需要 Argo CD 已安裝在 k3s cluster

## 關聯

- 依賴：ADR-116（MCP on k3s）
