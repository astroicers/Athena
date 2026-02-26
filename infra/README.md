# 基礎設施管理指南

> Athena 外部服務的安裝、啟動、管理與備份流程。

---

## 目錄

- [Caldera（執行引擎）](#caldera)
- [PentestGPT（研究參考）](#pentestgpt)
- [版本相容性矩陣](#版本相容性矩陣)

---

## Caldera

### 概覽

MITRE Caldera 是 Athena 的主要執行引擎，負責 OODA Act 階段的 MITRE ATT&CK 技術執行。

| 項目 | 內容 |
|------|------|
| 版本 | v5.3.0（已測試） |
| 授權 | Apache 2.0 |
| 來源 | `~/vendor/caldera/` |
| Docker | `ghcr.io/mitre/caldera:latest` |
| Port | 8888 |
| API | REST v2（`/api/v2/`） |

### 安裝

```bash
# 1. Clone（首次設定）
make vendor-init

# 2. 啟動容器
make caldera-up

# 3. 確認健康
make caldera-status
```

### 日常操作

```bash
# 啟動
make caldera-up

# 停止
make caldera-down

# 查看日誌
make caldera-logs

# 檢查狀態 + 版本
make caldera-status
```

### 模式切換

```bash
# 切換至真實 Caldera 模式
make real-mode
# 然後重啟 Athena backend

# 切回 Mock 模式
make mock-mode
# 然後重啟 Athena backend
```

### 備份與還原

```bash
# 備份 Caldera 資料
make caldera-backup
# 備份檔案：backups/caldera-data-YYYY-MM-DD.tar.gz

# 還原（手動）
docker volume rm athena_caldera-data
docker volume create athena_caldera-data
docker run --rm -v athena_caldera-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/caldera-data-YYYY-MM-DD.tar.gz -C /data
```

### 更新 Caldera

```bash
# 1. 停止容器
make caldera-down

# 2. 更新 vendor
cd ~/vendor/caldera
git fetch --tags
git checkout v5.x.x  # 新版本

# 3. 拉取新 Docker image
docker pull ghcr.io/mitre/caldera:latest

# 4. 重新啟動
make caldera-up

# 5. 驗證版本
make caldera-status
```

### Docker 網路注意事項

Athena backend 運行在 Docker 容器內時，`localhost` 指向容器自己，不是主機。

| 環境 | CALDERA_URL |
|------|-------------|
| Docker Desktop (macOS/Windows) | `http://host.docker.internal:8888` |
| WSL2 (Docker CE) | `http://172.17.0.1:8888` |
| 原生 Linux (Docker CE) | `http://172.17.0.1:8888` |
| 本機開發（無 Docker） | `http://localhost:8888` |

在 `.env` 或 `docker-compose.override.yml` 中設定 `CALDERA_URL`。

### 故障排除

| 問題 | 解法 |
|------|------|
| Health 顯示 "unreachable" | 確認 Caldera 容器運行中：`make caldera-status` |
| 容器內無法連線 | 檢查 `CALDERA_URL` 是否使用正確的 Docker 網路位址 |
| API 回應 401 | 設定 `CALDERA_API_KEY`（若 Caldera 啟用認證） |
| 版本警告 | Caldera 版本不在支援範圍（v4.x / v5.x），請確認相容性 |

---

## PentestGPT

### 概覽

PentestGPT 是自主滲透測試 Agent，Athena **不直接整合它**。保留 vendor clone 的目的：

1. **研究參考** — 學習其 prompt 工程技巧
2. **追蹤上游** — 關注新版本功能
3. **Phase 8 備用** — 未來可能透過 Docker API wrapper 整合

| 項目 | 內容 |
|------|------|
| 版本 | v1.0.0（USENIX Security 2024） |
| 授權 | MIT |
| 來源 | `~/vendor/PentestGPT/` |
| Python | 3.12+（與 Athena 3.11 不相容） |
| 介面 | CLI/TUI（Textual），無 REST API |

### 現狀

Athena 的 `OrientEngine`（`backend/app/services/orient_engine.py`）使用**自製 LLM prompt 工程**，
透過 Claude/GPT-4 API 產出戰術建議。設計受 PentestGPT 的方法論啟發，但不直接呼叫 PentestGPT。

### 不整合的原因

1. PentestGPT 是自主執行 Agent，非 advisory API
2. Python 3.12+ 需求與 Athena 3.11 衝突
3. 無原生 REST API，不改外部碼 = 無法加 wrapper
4. 現有 OrientEngine 已能產出高品質戰術建議

---

## 版本相容性矩陣

| 元件 | 已測試版本 | 支援範圍 | 備註 |
|------|-----------|---------|------|
| MITRE Caldera | v5.3.0 | v4.x, v5.x | API v2 |
| PentestGPT | v1.0.0 | — | 僅研究參考 |
| Python (Athena) | 3.11 | 3.11+ | 不升級至 3.12（PentestGPT 相容性） |
| Docker | 24.x+ | 20.10+ | Docker Compose V2 |
| Node.js | 20.x | 18+, 20+ | 前端建構 |

---

*最後更新：2026-02-26*
