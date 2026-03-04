# AI-SOP-Protocol — Makefile
# 目的：封裝重複指令，節省 Token，降低操作失誤風險
# 使用方式：依專案需求保留/修改對應區塊

APP_NAME ?= Athena
VERSION  ?= latest

.PHONY: help \
        build clean deploy logs up down docker-clean dev dev-backend dev-frontend seed \
        test test-backend test-frontend test-filter coverage lint \
        diagram \
        adr-new adr-list \
        spec-new spec-list \
        agent-done agent-status agent-reset agent-locks agent-unlock agent-lock-gc \
        session-checkpoint session-log \
        rag-index rag-search rag-stats rag-rebuild \
        guardrail-log guardrail-reset \
        c2-engine-init c2-engine-up c2-engine-down c2-engine-logs c2-engine-status c2-engine-backup \
        real-mode mock-mode \
        new-tool

#---------------------------------------------------------------------------
# Help
#---------------------------------------------------------------------------

help:
	@echo ""
	@echo "AI-SOP-Protocol 指令速查 — Athena"
	@echo "==================================="
	@echo ""
	@echo "🚀 Dev:         dev | dev-backend | dev-frontend | seed"
	@echo "📦 Container:   build | clean | deploy | logs"
	@echo "🧪 Test:        test | test-backend | test-frontend | test-filter FILTER=xxx | coverage | lint"
	@echo "📐 Docs:        diagram"
	@echo "📋 ADR:         adr-new TITLE=... | adr-list"
	@echo "📄 Spec:        spec-new TITLE=... | spec-list"
	@echo "🤖 Agent:       agent-done TASK=... STATUS=... | agent-status | agent-reset | agent-unlock FILE=... | agent-lock-gc"
	@echo "💾 Session:     session-checkpoint NEXT=... | session-log"
	@echo "🧠 RAG:         rag-index | rag-search Q=... | rag-stats | rag-rebuild"
	@echo "🛡  Guardrail:   guardrail-log | guardrail-reset"
	@echo ""

#---------------------------------------------------------------------------
# Docker / Container
#---------------------------------------------------------------------------

build:
	@echo "🔨 Building $(APP_NAME) services..."
	docker-compose build

clean:
	@echo "🧹 Cleaning..."
	rm -rf ./tmp/* 2>/dev/null || true
	rm -f backend/data/athena.db 2>/dev/null || true
	rm -rf backend/__pycache__ backend/app/__pycache__ 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules/.cache 2>/dev/null || true
	docker-compose down --rmi local --volumes --remove-orphans 2>/dev/null || true

deploy:
	@echo "🚀 Deploying $(APP_NAME):$(VERSION)..."
	docker-compose up -d --force-recreate
	docker-compose ps

logs:
	docker-compose logs -f --tail=100

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

#---------------------------------------------------------------------------
# Development
#---------------------------------------------------------------------------

dev:
	@echo "🚀 Starting full development environment..."
	docker-compose up --build

dev-backend:
	@echo "🐍 Starting backend (Python/FastAPI)..."
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	@echo "⚛️  Starting frontend (Next.js)..."
	cd frontend && npm run dev

seed:
	@echo "🌱 Loading demo seed data (OP-2024-017)..."
	cd backend && python3 -m app.seed.demo_scenario

#---------------------------------------------------------------------------
# Test
#---------------------------------------------------------------------------

test:
	@echo "🧪 Running all tests..."
	@echo "── Backend (pytest) ──"
	cd backend && python3 -m pytest tests/ -v --tb=short
	@echo ""
	@echo "── Frontend (npm test) ──"
	cd frontend && npm test

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && python3 -m pytest tests/ -v

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test

test-filter:
	@if [ -z "$(FILTER)" ]; then echo "使用方式：make test-filter FILTER=xxx"; exit 1; fi
	@echo "🧪 Running filtered: $(FILTER)"
	cd backend && python3 -m pytest tests/ -k "$(FILTER)" -v

coverage:
	@echo "📊 Running coverage report..."
	cd backend && python3 -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "Coverage HTML report: backend/htmlcov/index.html"

lint:
	@echo "🔍 Linting..."
	@echo "── Backend (ruff) ──"
	@cd backend && python3 -m ruff check . 2>/dev/null || (cd backend && python3 -m flake8 . 2>/dev/null) || echo "⚠️  請安裝 ruff 或 flake8"
	@echo ""
	@echo "── Frontend (next lint) ──"
	@cd frontend && npm run lint 2>/dev/null || echo "⚠️  前端 lint 尚未配置"

#---------------------------------------------------------------------------
# Architecture Diagram
#---------------------------------------------------------------------------

diagram:
	@echo "📐 Generating architecture diagram..."
	@# 從 architecture.md 提取 mermaid 區塊再餵給 mmdc
	@awk '/```mermaid/{flag=1;next}/```/{flag=0}flag' docs/architecture.md > /tmp/arch.mmd 2>/dev/null || true
	@mmdc -i /tmp/arch.mmd -o docs/architecture.png 2>/dev/null || \
	echo "⚠️  請安裝 mermaid-cli: npm install -g @mermaid-js/mermaid-cli"

#---------------------------------------------------------------------------
# ADR 管理
#---------------------------------------------------------------------------

adr-new:
	@if [ -z "$(TITLE)" ]; then read -p "ADR 標題: " TITLE; fi; \
	mkdir -p docs/adr; \
	COUNT=$$(ls docs/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' '); \
	NUM=$$(printf "%03d" $$((COUNT + 1))); \
	SLUG=$$(echo "$(TITLE)" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-'); \
	FILE="docs/adr/ADR-$$NUM-$$SLUG.md"; \
	cp .asp/templates/ADR_Template.md $$FILE; \
	SED_I=$$([ "$$(uname)" = "Darwin" ] && echo "sed -i ''" || echo "sed -i"); \
	$$SED_I "s/ADR-000/ADR-$$NUM/g" $$FILE; \
	$$SED_I "s/決策標題/$(TITLE)/g" $$FILE; \
	$$SED_I "s/YYYY-MM-DD/$$(date +%Y-%m-%d)/g" $$FILE; \
	echo "✅ 已建立: $$FILE"

adr-list:
	@echo "📋 ADR 列表："; \
	ls docs/adr/ADR-*.md 2>/dev/null | while read f; do \
		STATUS=$$(grep -m1 "狀態" $$f | grep -o '`[^`]*`' | tr -d '`'); \
		TITLE=$$(head -1 $$f | sed 's/# //'); \
		echo "  $$TITLE [$$STATUS]"; \
	done || echo "  (無 ADR)"

#---------------------------------------------------------------------------
# Spec 管理
#---------------------------------------------------------------------------

spec-new:
	@if [ -z "$(TITLE)" ]; then read -p "規格書標題: " TITLE; fi; \
	mkdir -p docs/specs; \
	COUNT=$$(ls docs/specs/SPEC-*.md 2>/dev/null | wc -l | tr -d ' '); \
	NUM=$$(printf "%03d" $$((COUNT + 1))); \
	SLUG=$$(echo "$(TITLE)" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-'); \
	FILE="docs/specs/SPEC-$$NUM-$$SLUG.md"; \
	cp .asp/templates/SPEC_Template.md $$FILE; \
	SED_I=$$([ "$$(uname)" = "Darwin" ] && echo "sed -i ''" || echo "sed -i"); \
	$$SED_I "s/SPEC-000/SPEC-$$NUM/g" $$FILE; \
	$$SED_I "s/功能名稱/$(TITLE)/g" $$FILE; \
	echo "✅ 已建立: $$FILE"

spec-list:
	@echo "📋 Spec 列表："; \
	ls docs/specs/SPEC-*.md 2>/dev/null | while read f; do echo "  $$f"; done || echo "  (無 Spec)"

#---------------------------------------------------------------------------
# Multi-Agent
#---------------------------------------------------------------------------

agent-done:
	@if [ -z "$(TASK)" ] || [ -z "$(STATUS)" ]; then \
		echo "使用方式：make agent-done TASK=TASK-001 STATUS=success"; exit 1; fi
	@mkdir -p .agent-events
	@echo "{\"task\":\"$(TASK)\",\"status\":\"$(STATUS)\",\"ts\":\"$$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"reason\":\"$(REASON)\"}" \
		>> .agent-events/completed.jsonl
	@echo "✅ Hook fired: $(TASK) → $(STATUS)"

agent-status:
	@echo "=== Agent 事件紀錄 ==="; \
	if [ -f .agent-events/completed.jsonl ]; then \
		python3 -c "import sys,json; \
[print(f'  [{l[\"status\"].upper()}] {l[\"task\"]} @ {l[\"ts\"]}') \
for l in (json.loads(x) for x in open('.agent-events/completed.jsonl'))]" 2>/dev/null || \
		cat .agent-events/completed.jsonl; \
	else echo "  (無事件紀錄)"; fi

agent-reset:
	@rm -f .agent-events/completed.jsonl
	@echo "🧹 Agent 事件紀錄已清空"

agent-unlock:
	@if [ -z "$(FILE)" ]; then echo "使用方式：make agent-unlock FILE=src/store/user.go"; exit 1; fi
	@if [ -f .agent-lock.yaml ]; then \
		python3 -c "import yaml; data = yaml.safe_load(open('.agent-lock.yaml')) or {}; data.get('locked_files', {}).pop('$(FILE)', None); yaml.dump(data, open('.agent-lock.yaml','w')); print('🔓 已解鎖: $(FILE)')" 2>/dev/null || echo "⚠️  需要 pip install pyyaml"; \
	else echo "  (無鎖定記錄)"; fi

agent-lock-gc:
	@echo "🧹 清理逾時鎖定（> 2 小時）..."
	@if [ -f .agent-lock.yaml ]; then \
		python3 -c "import yaml,datetime; f=open('.agent-lock.yaml'); data=yaml.safe_load(f) or {}; f.close(); locks=data.get('locked_files',{}); now=datetime.datetime.utcnow(); removed=[k for k,v in list(locks.items()) if now>datetime.datetime.fromisoformat(v.get('expires','2000-01-01').replace('Z',''))]; [locks.pop(k) for k in removed]; yaml.dump(data,open('.agent-lock.yaml','w')); print(f'已清理 {len(removed)} 個逾時鎖定：{removed}' if removed else '無逾時鎖定')" 2>/dev/null || echo "⚠️  需要 pip install pyyaml"; \
	else echo "  (無鎖定記錄)"; fi

agent-locks:
	@if [ -f .agent-lock.yaml ]; then \
		echo "🔒 文件鎖定清單："; cat .agent-lock.yaml; \
	else echo "  (無文件鎖定)"; fi

#---------------------------------------------------------------------------
# Session 管理
#---------------------------------------------------------------------------

session-checkpoint:
	@mkdir -p docs
	@printf "\n## Checkpoint：$$(date '+%Y-%m-%d %H:%M')\n- 當前任務：$(TASK)\n- 狀態：$(STATUS)\n- 下一步：$(NEXT)\n" \
		>> docs/session-log.md
	@echo "✅ Checkpoint 已儲存"

session-log:
	@tail -30 docs/session-log.md 2>/dev/null || echo "(無 Session 紀錄)"

#---------------------------------------------------------------------------
# RAG 知識庫
#---------------------------------------------------------------------------

rag-index:
	@echo "🔍 Building RAG index..."
	@python3 .asp/scripts/rag/build_index.py \
		--source docs/ \
		--source .asp/profiles/ \
		--output .rag/index \
		--model all-MiniLM-L6-v2 2>/dev/null || \
	echo "⚠️  請先執行: pip install chromadb sentence-transformers"

rag-search:
	@if [ -z "$(Q)" ]; then echo "使用方式：make rag-search Q=\"你的問題\""; exit 1; fi
	@python3 .asp/scripts/rag/search.py --query "$(Q)" --top-k 3 2>/dev/null || \
	echo "⚠️  RAG 尚未初始化，請先執行 make rag-index"

rag-stats:
	@python3 .asp/scripts/rag/stats.py 2>/dev/null || \
	echo "⚠️  RAG 尚未初始化，請先執行 make rag-index"

rag-rebuild:
	@rm -rf .rag/index
	@$(MAKE) rag-index

#---------------------------------------------------------------------------
# Guardrail
#---------------------------------------------------------------------------

guardrail-log:
	@if [ -f .guardrail/rejected.jsonl ]; then \
		python3 -c "import json; \
[print(f'[{l[\"type\"]}] {l[\"ts\"]}: {l[\"query\"][:60]}...') \
for l in (json.loads(x) for x in open('.guardrail/rejected.jsonl'))]" 2>/dev/null; \
	else echo "(無護欄觸發紀錄)"; fi

guardrail-reset:
	@rm -f .guardrail/rejected.jsonl
	@echo "🧹 護欄紀錄已清除"

#---------------------------------------------------------------------------
# Vendor / 外部專案管理
#---------------------------------------------------------------------------

C2_ENGINE_COMPOSE := infra/c2-engine/docker-compose.c2-engine.yml

c2-engine-init:  ## 初始化 C2 引擎配置
	@mkdir -p infra/c2-engine
	@echo "C2 engine config directory ready."



c2-engine-up:  ## 啟動 C2 引擎容器
	@echo "Starting C2 engine..."
	docker compose --profile c2-engine up -d c2-engine
	@echo "C2 engine: http://localhost:58888"

c2-engine-down:  ## 停止 C2 引擎容器
	@echo "Stopping C2 engine..."
	docker compose --profile c2-engine stop c2-engine

c2-engine-logs:  ## 查看 C2 引擎日誌
	docker compose --profile c2-engine logs -f --tail=100 c2-engine

c2-engine-status:  ## 檢查 C2 引擎健康 + 版本
	@echo "=== C2 Engine Status ==="
	@docker compose --profile c2-engine ps c2-engine 2>/dev/null || echo "  Container: not running"
	@echo ""
	@curl -sf http://localhost:58888/api/v2/health > /dev/null 2>&1 \
		&& echo "  Health: OK" \
		|| echo "  Health: unreachable"

c2-engine-backup:  ## 備份 C2 引擎 data volume
	@mkdir -p backups
	@BACKUP_FILE="backups/c2-engine-data-$$(date +%Y-%m-%d).tar.gz"; \
	docker run --rm \
		-v athena_c2-engine-data:/data:ro \
		-v $$(pwd)/backups:/backup \
		alpine tar czf /backup/$$(basename $$BACKUP_FILE) -C /data . && \
	echo "Backup saved: $$BACKUP_FILE"

#---------------------------------------------------------------------------
# 模式切換
#---------------------------------------------------------------------------

real-mode:  ## .env 切為真實模式（MOCK_*=false）
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@sed -i '/^MOCK_CALDERA=/d' .env
	@grep -q '^MOCK_C2_ENGINE=' .env && sed -i 's/^MOCK_C2_ENGINE=.*/MOCK_C2_ENGINE=false/' .env || echo 'MOCK_C2_ENGINE=false' >> .env
	@grep -q '^MOCK_LLM=' .env && sed -i 's/^MOCK_LLM=.*/MOCK_LLM=false/' .env || echo 'MOCK_LLM=false' >> .env
	@grep -q '^MOCK_METASPLOIT=' .env && sed -i 's/^MOCK_METASPLOIT=.*/MOCK_METASPLOIT=false/' .env || echo 'MOCK_METASPLOIT=false' >> .env
	@echo "✅ Real mode enabled. Restart Athena to apply."
	@echo "   確認 C2 引擎運行中: make c2-engine-status"
	@echo "   確認 LLM API key 已設定: grep API_KEY .env"

mock-mode:  ## .env 切為 mock 模式（MOCK_*=true）
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@sed -i '/^MOCK_CALDERA=/d' .env
	@grep -q '^MOCK_C2_ENGINE=' .env && sed -i 's/^MOCK_C2_ENGINE=.*/MOCK_C2_ENGINE=true/' .env || echo 'MOCK_C2_ENGINE=true' >> .env
	@grep -q '^MOCK_LLM=' .env && sed -i 's/^MOCK_LLM=.*/MOCK_LLM=true/' .env || echo 'MOCK_LLM=true' >> .env
	@grep -q '^MOCK_METASPLOIT=' .env && sed -i 's/^MOCK_METASPLOIT=.*/MOCK_METASPLOIT=true/' .env || echo 'MOCK_METASPLOIT=true' >> .env
	@echo "✅ Mock mode enabled. Restart Athena to apply."

#---------------------------------------------------------------------------
# MCP Tool Scaffolding
#---------------------------------------------------------------------------

new-tool:  ## 建立新的 MCP tool server scaffold（用法: make new-tool NAME=my-scanner）
	@if [ -z "$(NAME)" ]; then echo "Usage: make new-tool NAME=my-scanner"; exit 1; fi
	@mkdir -p tools/$(NAME)
	@cp tools/_template/pyproject.toml tools/$(NAME)/pyproject.toml
	@cp tools/_template/Dockerfile tools/$(NAME)/Dockerfile
	@cp tools/_template/server.py tools/$(NAME)/server.py
	@cp tools/_template/README.md tools/$(NAME)/README.md
	@sed -i "s/{{TOOL_NAME}}/$(NAME)/g" tools/$(NAME)/pyproject.toml tools/$(NAME)/Dockerfile tools/$(NAME)/server.py tools/$(NAME)/README.md
	@echo "✅ MCP tool scaffold created: tools/$(NAME)/"
	@echo "   Next steps:"
	@echo "   1. Edit tools/$(NAME)/server.py — add your tool logic"
	@echo "   2. Add server entry to mcp_servers.json"
	@echo "   3. Register in tool_registry via POST /api/tools"
