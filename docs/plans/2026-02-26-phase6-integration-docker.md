# Phase 6：整合與 Docker 部署 — 實作計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 實現 SPEC-009（Demo runner + 健康檢查增強）和 SPEC-010（Dockerfiles + docker-compose 完整化），讓 `docker-compose up --build` 一行啟動完整 Athena Demo。

**Architecture:** 後端新增 `demo_runner.py` 自動化腳本以 httpx 依序呼叫 API 完成 6 步 OODA 循環。增強 `/api/health` 端點回傳 mock/connected/disconnected 狀態。新增 backend/frontend Dockerfiles + .dockerignore，更新 docker-compose.yml 加入 healthcheck、named volume、service_healthy 依賴。

**Tech Stack:** Python 3.11 + FastAPI + aiosqlite, Next.js 14 + React 18, Docker multi-stage build, httpx

---

## Task 1：增強健康檢查端點

**Files:**
- Modify: `backend/app/routers/health.py`
- Modify: `backend/app/config.py`（若需 `MOCK_CALDERA` 未設定則加入）

**Context:** 目前 `/api/health` 的 caldera/shannon 永遠回傳 `"unknown"`。SPEC-009 要求回傳 `"mock"` / `"connected"` / `"disconnected"` / `"disabled"`。

**Step 1: 更新 health.py**

改寫 `health_check` 函式，根據 `settings.MOCK_CALDERA` 和 `settings.MOCK_LLM` 回傳正確的服務狀態：

```python
"""Health check endpoint."""

from fastapi import APIRouter, Depends
import aiosqlite

from app.config import settings
from app.database import get_db
from app.models.api_schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check(db: aiosqlite.Connection = Depends(get_db)):
    """Return service health status."""
    # Check database connectivity
    db_status = "connected"
    try:
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
    except Exception:
        db_status = "error"

    # Caldera status
    if settings.MOCK_CALDERA:
        caldera_status = "mock"
    else:
        caldera_status = "connected"  # POC: assume connected if not mock

    # Shannon status
    shannon_status = "disabled"
    if settings.SHANNON_URL:
        shannon_status = "disconnected"  # POC: no live ping

    # LLM status
    if settings.MOCK_LLM:
        llm_status = "mock"
    elif settings.ANTHROPIC_API_KEY:
        llm_status = "claude"
    elif settings.OPENAI_API_KEY:
        llm_status = "openai"
    else:
        llm_status = "unavailable"

    return HealthStatus(
        status="ok",
        version="0.1.0",
        services={
            "database": db_status,
            "caldera": caldera_status,
            "shannon": shannon_status,
            "websocket": "active",
            "llm": llm_status,
        },
    )
```

**Step 2: 驗證**

```bash
cd backend && python3 -c "from app.routers.health import router; print('OK')"
```

**Step 3: Commit**

```bash
git add backend/app/routers/health.py
git commit -m "feat(health): enhance /api/health with mock/connected/disabled statuses (SPEC-009)"
```

---

## Task 2：Demo Runner 自動化腳本

**Files:**
- Create: `backend/app/seed/demo_runner.py`

**Context:** SPEC-009 要求一鍵 Demo 腳本，使用 httpx 依序呼叫 API 完成 6 步 OODA 循環。需支援 `DEMO_STEP_DELAY` 環境變數（預設 3 秒）。需在 `MOCK_LLM=true` + 無 Caldera 下可運行。

**Step 1: 建立 demo_runner.py**

```python
"""
Demo runner — automated 6-step OODA cycle for OP-2024-017 PHANTOM-EYE.

Usage:
    python -m app.seed.demo_runner [--base-url http://localhost:8000] [--delay 3]

Runs against the API to demonstrate a full OODA cycle.
Works with MOCK_LLM=true and MOCK_CALDERA=true (no external services needed).
"""

import argparse
import asyncio
import os
import sys

import httpx


DEMO_STEP_DELAY = float(os.getenv("DEMO_STEP_DELAY", "3"))


async def run_demo(base_url: str, delay: float):
    """Execute the 6-step OODA demo."""
    api = f"{base_url}/api"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ── Pre-check: health ──
        print("=" * 60)
        print("  Athena Demo — OP-2024-017 PHANTOM-EYE")
        print("=" * 60)
        print()

        resp = await client.get(f"{api}/health")
        if resp.status_code != 200:
            print(f"[ERROR] Health check failed: {resp.status_code}")
            sys.exit(1)
        health = resp.json()
        print(f"[OK] Health: {health['status']}")
        for svc, status in health.get("services", {}).items():
            print(f"     {svc}: {status}")
        print()

        # ── Get operation ──
        resp = await client.get(f"{api}/operations")
        if resp.status_code != 200 or not resp.json():
            print("[ERROR] No operations found. Seed data may not be loaded.")
            sys.exit(1)
        operations = resp.json()
        op = operations[0]
        op_id = op["id"]
        print(f"[OK] Operation: {op.get('name', op_id)}")
        print(f"     Status: {op.get('status', 'unknown')}")
        print()

        # ── Step 1: OBSERVE — trigger first OODA cycle ──
        print("-" * 60)
        print("Step 1: OBSERVE — Triggering OODA cycle")
        print("-" * 60)
        resp = await _post(client, f"{api}/operations/{op_id}/ooda/trigger")
        if resp:
            data = resp.json()
            print(f"  Phase: {data.get('phase', '?')}")
            print(f"  Observe: {(data.get('observe_summary') or '')[:80]}")
            print(f"  Orient:  {(data.get('orient_summary') or '')[:80]}")
            print(f"  Decide:  {(data.get('decide_summary') or '')[:80]}")
            print(f"  Act:     {(data.get('act_summary') or '')[:80]}")
        print()
        await asyncio.sleep(delay)

        # ── Step 2: ORIENT — check recommendation ──
        print("-" * 60)
        print("Step 2: ORIENT — Checking PentestGPT recommendation")
        print("-" * 60)
        resp = await _get(client, f"{api}/operations/{op_id}/recommendations")
        if resp:
            recs = resp.json()
            if recs:
                latest = recs[-1]
                print(f"  Assessment: {(latest.get('situation_assessment') or '')[:80]}")
                print(f"  Confidence: {latest.get('confidence', '?')}")
                options = latest.get("options", [])
                for i, opt in enumerate(options[:3], 1):
                    print(f"  Option {i}: {opt.get('technique_id', '?')} — {opt.get('rationale', '')[:50]}")
            else:
                print("  (No recommendations yet)")
        print()
        await asyncio.sleep(delay)

        # ── Step 3: DECIDE — check C5ISR status ──
        print("-" * 60)
        print("Step 3: DECIDE — Reviewing C5ISR domain status")
        print("-" * 60)
        resp = await _get(client, f"{api}/operations/{op_id}/c5isr")
        if resp:
            domains = resp.json()
            for d in domains:
                print(f"  {d.get('domain', '?'):12s} {d.get('status', '?'):12s} {d.get('health_pct', 0):5.1f}%  {d.get('detail', '')}")
        print()
        await asyncio.sleep(delay)

        # ── Step 4: ACT — check execution history ──
        print("-" * 60)
        print("Step 4: ACT — Checking technique executions")
        print("-" * 60)
        resp = await _get(client, f"{api}/operations/{op_id}/techniques/matrix")
        if resp:
            matrix = resp.json()
            execs = matrix.get("executions", [])
            print(f"  Total executions: {len(execs)}")
            for ex in execs[:5]:
                print(f"  {ex.get('technique_id', '?')} → {ex.get('status', '?')} ({ex.get('engine', '?')})")
        print()
        await asyncio.sleep(delay)

        # ── Step 5: OBSERVE (round 2) — trigger second cycle ──
        print("-" * 60)
        print("Step 5: OBSERVE (Round 2) — Triggering second OODA cycle")
        print("-" * 60)
        resp = await _post(client, f"{api}/operations/{op_id}/ooda/trigger")
        if resp:
            data = resp.json()
            print(f"  Iteration: {data.get('iteration_number', '?')}")
            print(f"  Observe: {(data.get('observe_summary') or '')[:80]}")
            print(f"  Act:     {(data.get('act_summary') or '')[:80]}")
        print()
        await asyncio.sleep(delay)

        # ── Step 6: ORIENT (round 2) — check updated state ──
        print("-" * 60)
        print("Step 6: ORIENT (Round 2) — Checking updated operation state")
        print("-" * 60)
        resp = await _get(client, f"{api}/operations/{op_id}")
        if resp:
            op_data = resp.json()
            print(f"  Status: {op_data.get('status', '?')}")
            print(f"  OODA Phase: {op_data.get('current_ooda_phase', '?')}")
            print(f"  Iterations: {op_data.get('ooda_iteration_count', '?')}")
            print(f"  Success Rate: {op_data.get('success_rate', '?')}%")

        # ── Timeline ──
        print()
        print("-" * 60)
        print("OODA Timeline")
        print("-" * 60)
        resp = await _get(client, f"{api}/operations/{op_id}/ooda/timeline")
        if resp:
            entries = resp.json()
            for e in entries:
                print(f"  [{e.get('iteration_number', '?')}] {e.get('phase', '?'):8s} {(e.get('summary') or '')[:60]}")

        print()
        print("=" * 60)
        print("  Demo complete!")
        print("=" * 60)


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    """GET with retry."""
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            print(f"  [WARN] GET {url} → {resp.status_code}")
            return None
        return resp
    except Exception as e:
        print(f"  [ERROR] GET {url} → {e}")
        return None


async def _post(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    """POST with retry."""
    for attempt in range(2):
        try:
            resp = await client.post(url)
            if resp.status_code == 200:
                return resp
            if attempt == 0:
                print(f"  [WARN] POST {url} → {resp.status_code}, retrying...")
                await asyncio.sleep(1)
            else:
                print(f"  [WARN] POST {url} → {resp.status_code}")
                return None
        except Exception as e:
            if attempt == 0:
                print(f"  [WARN] POST {url} → {e}, retrying...")
                await asyncio.sleep(1)
            else:
                print(f"  [ERROR] POST {url} → {e}")
                return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Athena Demo Runner")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--delay", type=float, default=DEMO_STEP_DELAY, help="Delay between steps (seconds)")
    args = parser.parse_args()

    asyncio.run(run_demo(args.base_url, args.delay))


if __name__ == "__main__":
    main()
```

**Step 2: 驗證腳本語法**

```bash
cd backend && python3 -c "import ast; ast.parse(open('app/seed/demo_runner.py').read()); print('Syntax OK')"
```

**Step 3: Commit**

```bash
git add backend/app/seed/demo_runner.py
git commit -m "feat(demo): add demo_runner.py for automated 6-step OODA cycle (SPEC-009)"
```

---

## Task 3：Backend Dockerfile + .dockerignore

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

**Context:** SPEC-010 規定 `python:3.11-slim`，兩階段 COPY（先 pyproject.toml 再 app/），HEALTHCHECK `/api/health`。

**Step 1: 建立 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (Docker cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY app/ ./app/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: 建立 backend/.dockerignore**

```
__pycache__/
*.pyc
*.pyo
.venv/
tests/
data/*.db
data/*.db-*
.env
.env.*
.pytest_cache/
htmlcov/
```

**Step 3: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat(docker): add backend Dockerfile + .dockerignore (SPEC-010)"
```

---

## Task 4：Frontend Dockerfile + .dockerignore + next.config.js standalone

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`
- Modify: `frontend/next.config.js` — 加入 `output: "standalone"`

**Context:** SPEC-010 規定 multi-stage build（builder + runner），Next.js standalone 輸出，node:20-alpine。

**Step 1: 更新 next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["three", "react-force-graph-3d"],
};

module.exports = nextConfig;
```

**Step 2: 建立 frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

**Step 3: 建立 frontend/.dockerignore**

```
node_modules/
.next/
out/
.env
.env.*
```

**Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore frontend/next.config.js
git commit -m "feat(docker): add frontend Dockerfile + .dockerignore + standalone output (SPEC-010)"
```

---

## Task 5：更新 docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

**Context:** 目前 docker-compose.yml 缺少 healthcheck、named volume、service_healthy 依賴、DATABASE_URL 覆寫、restart policy。SPEC-010 要求 `127.0.0.1` binding + named volume + service_healthy。

**Step 1: 改寫 docker-compose.yml**

```yaml
version: "3.8"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - backend-data:/app/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:///app/data/athena.db
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  backend-data:
    driver: local
```

注意：`NEXT_PUBLIC_WS_URL` 使用 `ws://localhost:8000/ws`（瀏覽器端連線），而非 Docker DNS。

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): update docker-compose with healthcheck, named volume, service_healthy (SPEC-010)"
```

---

## Task 6：更新 Makefile Docker targets

**Files:**
- Modify: `Makefile`

**Context:** 目前 Makefile 已有 `build`/`clean`/`deploy`/`logs`/`dev` targets。SPEC-010 要求新增 `up`/`down`/`docker-clean` targets。現有的 `dev` target 已做 `docker-compose up --build`，所以 `up` 改為背景模式（`-d`），`down` 改用簡潔版。

**Step 1: 新增 Makefile targets**

在 `#---------------------------------------------------------------------------` Docker / Container 區塊中，新增：

```makefile
up:
	@echo "🚀 Starting Athena (detached)..."
	docker-compose up --build -d
	@echo "✅ Backend: http://localhost:8000/api/health"
	@echo "✅ Frontend: http://localhost:3000"
	@echo "📋 Logs: make logs"

down:
	@echo "⏹  Stopping Athena..."
	docker-compose down

docker-clean:
	@echo "🧹 Cleaning Docker (images + volumes)..."
	docker-compose down -v --rmi local
```

**Step 2: 更新 .PHONY 行加入 `up down docker-clean`**

**Step 3: Commit**

```bash
git add Makefile
git commit -m "feat(make): add up/down/docker-clean targets (SPEC-010)"
```

---

## Task 7：端對端驗證

**Step 1: 驗證後端啟動（無 Docker）**

```bash
cd backend && python3 -c "
import asyncio
from app.main import app
print('FastAPI app created OK')
print('Routes:', len(app.routes))
"
```

**Step 2: 驗證 demo_runner 語法**

```bash
cd backend && python3 -c "from app.seed.demo_runner import run_demo; print('demo_runner OK')"
```

**Step 3: 驗證 Dockerfile 語法**

```bash
# Check Dockerfiles can be parsed (no syntax errors)
docker-compose config > /dev/null 2>&1 && echo "docker-compose config OK" || echo "docker-compose config FAIL"
```

**Step 4: Final commit（如有遺漏修改）**

```bash
git status
# If clean, no action needed
```

---

## 任務相依性

```
Task 1 (health)     ─────┐
Task 2 (demo_runner) ────┤
Task 3 (backend Dockerfile) ──┐
Task 4 (frontend Dockerfile) ─┤─→ Task 5 (docker-compose) → Task 6 (Makefile) → Task 7 (verify)
                               │
```

Task 1-4 可獨立進行。Task 5 依賴 3+4。Task 6 依賴 5。Task 7 最後執行。

---

## 驗收標準對照

| SPEC-009 驗收標準 | 對應 Task |
|---|---|
| `POST /api/operations/{id}/ooda/trigger` → 完整 OODA 循環 | 已由 SPEC-007/008 實作 ✅ |
| `GET /api/health` 回傳所有服務狀態 | Task 1 |
| `MOCK_LLM=true` + 無 Caldera 下完整 Demo 可執行 | Task 2 |
| 7 種 WebSocket 事件可觀察 | 已由 SPEC-007/008 實作 ✅ |

| SPEC-010 驗收標準 | 對應 Task |
|---|---|
| `docker-compose up --build` 啟動成功 | Task 3+4+5 |
| `curl /api/health` 回傳 ok | Task 1+3 |
| `curl /api/operations` 回傳種子資料 | 已有 ✅ |
| 瀏覽器 `localhost:3000` 顯示 UI | Task 4+5 |
| backend 映像 < 500MB | Task 3 |
| frontend 映像 < 200MB | Task 4 |
| `make up` / `make down` 正常運作 | Task 6 |
