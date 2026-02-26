# 貢獻指南 Contributing Guide

感謝您有興趣為 Athena 貢獻！以下指南將幫助您快速上手。

---

## 開發環境設定 Development Setup

### 前置需求

- Docker + Docker Compose v2
- Python 3.11+（後端開發）
- Node.js 20+（前端開發）
- Git

### 快速啟動

```bash
# 1. Fork 並 clone
git clone https://github.com/<your-username>/Athena.git
cd Athena

# 2. 複製環境設定
cp .env.example .env

# 3. 啟動服務（Docker）
make up

# 4. 驗證
curl http://localhost:8000/api/health
```

### 本地開發（不使用 Docker）

```bash
# 後端
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

詳細設定步驟請參閱 [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)。

---

## 專案結構 Project Structure

```
Athena/
├── backend/          # Python 3.11 + FastAPI
│   └── app/
│       ├── models/       # Pydantic 資料模型
│       ├── routers/      # REST API 路由
│       ├── services/     # 核心業務邏輯（OODA、C5ISR）
│       ├── clients/      # 外部引擎客戶端（Caldera、Shannon）
│       └── seed/         # Demo 種子資料與 runner
├── frontend/         # Next.js 14 + React 18 + Tailwind v4
│   └── src/
│       ├── app/          # 頁面路由
│       ├── components/   # UI 元件
│       ├── hooks/        # 自訂 Hooks
│       ├── lib/          # API 客戶端、常數
│       └── types/        # TypeScript 型別定義
├── infra/            # 基礎設施配置
├── docs/             # 文件
└── design/           # Pencil.dev 設計稿
```

完整架構說明請參閱 [docs/architecture/](docs/architecture/)。

---

## 工作流程 Workflow

### 1. 建立分支

```bash
git checkout -b feat/your-feature-name
```

分支命名規範：
- `feat/` — 新功能
- `fix/` — 修復 Bug
- `docs/` — 文件更新
- `chore/` — 維護性變更

### 2. 開發與測試

```bash
# 後端 lint
cd backend && ruff check app/

# 前端 lint + build
cd frontend && npm run lint && npm run build

# 跑測試
make test
```

### 3. 提交 Commit

遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hant/)：

```
feat: 新增 C5ISR 指標匯出功能
fix: 修復 OODA 循環狀態機跳轉錯誤
docs: 更新 API 文件
chore: 升級依賴版本
ci: 修正 GitHub Actions 快取路徑
```

### 4. 建立 Pull Request

- 確保 CI 通過
- 填寫 PR 模板
- 連結相關 Issue

---

## 程式碼規範 Coding Standards

### Python（後端）

- 遵循 PEP 8（由 Ruff 檢查）
- 使用 type hints
- 使用 `async`/`await`（FastAPI 原生非同步）
- 行寬上限 100 字元

```python
# 好的
async def get_operation(operation_id: str, db: aiosqlite.Connection) -> Operation:
    ...

# 不好的
def get_operation(operation_id, db):
    ...
```

### TypeScript（前端）

- 啟用 strict mode
- 使用 functional components
- Props 型別使用 interface 定義

```typescript
// 好的
interface MetricCardProps {
  label: string;
  value: number;
  trend?: "up" | "down";
}

export function MetricCard({ label, value, trend }: MetricCardProps) {
  ...
}
```

### License Header

所有新的原始碼檔案**必須**包含 Apache 2.0 授權標頭：

```python
# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...（完整 14 行）
```

可使用 `python3 scripts/add_license_headers.py` 批次新增。

---

## 測試 Testing

```bash
# 後端測試
cd backend && pytest tests/ -v

# 前端 lint（目前無單元測試框架）
cd frontend && npm run lint

# 完整 CI 驗證
make test
```

> **注意**：POC 階段測試覆蓋率有限。歡迎貢獻測試！

---

## Issue 與 PR 規範

### Issue

- 使用 Issue 模板（Bug Report 或 Feature Request）
- 清楚描述問題或需求
- 附上重現步驟（Bug）或使用情境（Feature）

### Pull Request

- 一個 PR 聚焦一件事
- 保持 PR 精簡（< 500 行為佳）
- 填寫 PR 模板中的所有欄位
- 確保 CI 通過後再請求 review

---

## 授權 License

本專案採用 [Apache License 2.0](LICENSE)。

提交 Pull Request 即表示您同意將您的貢獻以 Apache 2.0 授權發佈。
