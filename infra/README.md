# 基礎設施管理指南

> Athena 外部服務的安裝、啟動、管理與備份流程。

---

## 目錄

- [C2 Engine（執行引擎）](#c2-engine)
- [版本相容性矩陣](#版本相容性矩陣)

---

## C2 Engine

### 概覽

C2 Engine 是 Athena 的主要執行引擎，負責 OODA Act 階段的 MITRE ATT&CK 技術執行。

| 項目 | 內容 |
|------|------|
| 版本 | v5.3.0（已測試） |
| 授權 | Apache 2.0 |
| Docker | `ghcr.io/mitre/caldera:latest` |
| Port | 8888 |
| API | REST v2（`/api/v2/`） |

### 安裝

```bash
# 1. 初始化配置目錄（首次設定）
make c2-engine-init

# 2. 啟動容器
make c2-engine-up

# 3. 確認健康
make c2-engine-status
```

### 日常操作

```bash
# 啟動
make c2-engine-up

# 停止
make c2-engine-down

# 查看日誌
make c2-engine-logs

# 檢查狀態 + 版本
make c2-engine-status
```

### 模式切換

```bash
# 切換至真實 C2 引擎模式
make real-mode
# 然後重啟 Athena backend

# 切回 Mock 模式
make mock-mode
# 然後重啟 Athena backend
```

### 備份與還原

```bash
# 備份 C2 引擎資料
make c2-engine-backup
# 備份檔案：backups/c2-engine-data-YYYY-MM-DD.tar.gz

# 還原（手動）
docker volume rm athena_c2-engine-data
docker volume create athena_c2-engine-data
docker run --rm -v athena_c2-engine-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/c2-engine-data-YYYY-MM-DD.tar.gz -C /data
```

### 更新 C2 Engine

```bash
# 1. 停止容器
make c2-engine-down

# 2. 拉取新 Docker image
docker pull ghcr.io/mitre/caldera:latest

# 3. 重新啟動
make c2-engine-up

# 4. 驗證版本
make c2-engine-status
```

### Docker 網路注意事項

Athena backend 運行在 Docker 容器內時，`localhost` 指向容器自己，不是主機。

| 環境 | C2_ENGINE_URL |
|------|---------------|
| Docker Desktop (macOS/Windows) | `http://host.docker.internal:8888` |
| WSL2 (Docker CE) | `http://172.17.0.1:8888` |
| 原生 Linux (Docker CE) | `http://172.17.0.1:8888` |
| 本機開發（無 Docker） | `http://localhost:8888` |

在 `.env` 或 `docker-compose.override.yml` 中設定 `C2_ENGINE_URL`。

### 故障排除

| 問題 | 解法 |
|------|------|
| Health 顯示 "unreachable" | 確認 C2 引擎容器運行中：`make c2-engine-status` |
| 容器內無法連線 | 檢查 `C2_ENGINE_URL` 是否使用正確的 Docker 網路位址 |
| API 回應 401 | 設定 `C2_ENGINE_API_KEY`（若 C2 引擎啟用認證） |
| 版本警告 | 確認使用的映像版本在支援範圍內（v4.x / v5.x） |

---

## 版本相容性矩陣

| 元件 | 已測試版本 | 支援範圍 | 備註 |
|------|-----------|---------|------|
| C2 Engine | v5.3.0 | v4.x, v5.x | API v2 |
| Python (Athena) | 3.11 | 3.11+ | |
| Docker | 24.x+ | 20.10+ | Docker Compose V2 |
| Node.js | 20.x | 18+, 20+ | 前端建構 |

---

*最後更新：2026-03-02*
