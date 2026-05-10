# [ADR-103]: Bearer Token 認證

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-05-10 |
| **決策者** | Athena Team |

## 背景

ADR-011（v1.x）選擇無認證以加速開發，但這在任何暴露於網路的環境都是不可接受的。

## 決策

`athena-api` 的所有路由（`/api/health` 除外）強制要求 `Authorization: Bearer <token>` header。Token 從 `ATHENA_SERVER__API_KEY` 環境變數讀取，在 `athena-config` 初始化時載入。

## 關聯

- 取代：ADR-011
