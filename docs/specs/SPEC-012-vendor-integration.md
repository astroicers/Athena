# SPEC-012：外部專案整合（PentestGPT + Caldera）

> 結構完整的規格書讓 AI 零確認直接執行。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-012 |
| **關聯 ADR** | ADR-005, ADR-006 |
| **估算複雜度** | 中 |
| **建議模型** | Opus |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> 將 PentestGPT 和 MITRE Caldera 兩個外部開源專案整合進 Athena 的運行環境，建立 vendor 管理流程、修復已識別的 12 個 Gap（Critical 3 + High 5 + Medium 4），並確保 mock/real 模式平滑切換。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| CALDERA_URL | string | .env | 有效 URL，含 port |
| CALDERA_API_KEY | string | .env | 選填（POC 可空） |
| MOCK_CALDERA | bool | .env | true=mock, false=真實 |
| MOCK_LLM | bool | .env | true=mock, false=真實 |
| ANTHROPIC_API_KEY | string | .env | 真實 LLM 模式必填 |

---

## 📤 輸出規格（Expected Output）

**健康檢查回應（`GET /api/health`）：**

Mock 模式：
```json
{
  "status": "ok",
  "version": "0.1.0",
  "services": {
    "database": "connected",
    "caldera": "mock",
    "shannon": "disabled",
    "websocket": "active",
    "llm": "mock"
  }
}
```

真實 Caldera 模式：
```json
{
  "services": {
    "caldera": "connected"
  }
}
```

Caldera 不可用時：
```json
{
  "services": {
    "caldera": "unreachable"
  }
}
```

**Agent Sync 回應（`POST /operations/{id}/agents/sync`）：**

Mock 模式：
```json
{"message": "Mock mode — using seed agents", "synced": 0}
```

真實模式：
```json
{"synced": 3}
```

**失敗情境：**

| 錯誤類型 | HTTP Code | 處理方式 |
|----------|-----------|----------|
| Caldera 無法連線 | 200 | health 回報 "unreachable"（不 crash） |
| Caldera API 暫時失敗 | — | CalderaClient 自動重試 3 次 |
| Caldera 版本不支援 | — | 啟動時 warning log，不阻擋 |
| Agent sync 在 mock 模式 | 200 | 回傳 synced: 0 |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1：Docker 容器內 `localhost:8888` 無法存取主機 Caldera → 需用 `host.docker.internal`
- Case 2：Caldera 啟動中但尚未就緒 → health 回報 "unreachable"，不 crash
- Case 3：CalderaClient 重試 3 次後仍失敗 → 回傳 ExecutionResult(success=False)
- Case 4：MOCK_CALDERA 切換時不需重啟（但建議重啟確保乾淨狀態）
- Case 5：vendor/ 目錄不存在時，Makefile targets 應提示 `make vendor-init`

---

## ✅ 驗收標準（Done When）

- [x] `make vendor-init` 可成功 clone 兩個外部專案到 `~/vendor/`
- [x] `make caldera-up` 可啟動 Caldera Docker 容器
- [x] `make caldera-status` 可查看 Caldera 健康狀態與版本
- [x] `curl :8500/api/health` 在 mock 模式回報 `caldera: "mock"`
- [x] `curl :8500/api/health` 在真實模式回報 `caldera: "connected"` 或 `"unreachable"`
- [x] CalderaClient.execute() 有 3 次重試機制
- [x] CalderaClient.check_version() 可檢查版本相容性
- [x] Agent sync endpoint 在 mock 模式回傳 `synced: 0`
- [x] Agent sync endpoint 在真實模式可從 Caldera 同步 agents
- [x] `config.py` 已移除未使用的 `PENTESTGPT_API_URL` 和 `PENTESTGPT_MODEL`
- [x] `.env.example` 包含 Docker 網路說明
- [x] `infra/README.md` 包含 Caldera 管理指引
- [x] `make lint` 無 error
- [x] Demo runner 在 mock 模式仍正常執行
- [x] 已更新 `docs/architecture.md`

---

## 🚫 禁止事項（Out of Scope）

- 不要修改：PentestGPT 或 Caldera 原始碼
- 不要引入新依賴：不加入 PentestGPT Python 套件（版本衝突）
- 不要實作 Shannon 整合
- 不要升級 Python 至 3.12
- 不要實作 Phase 8 項目（監控、PostgreSQL）

---

## 📎 參考資料（References）

- 相關 ADR：ADR-005（PentestGPT Orient 引擎）、ADR-006（執行引擎抽象與授權隔離）
- Gap 分析：30 項（本 SPEC 修復 12 項，Critical 3 + High 5 + Medium 4）
- 整合計畫：`/home/ubuntu/.claude/plans/cosmic-wibbling-walrus.md`
- Caldera API 文件：https://caldera.readthedocs.io/
- PentestGPT 論文：USENIX Security 2024
