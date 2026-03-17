# AI-SOP-Protocol — ASP Targets (included by project Makefile)
# 勿直接編輯此檔案，升級 ASP 時會自動覆蓋
# ASP_MAKEFILE_VERSION=2.5.0

# --- 條件載入：讀取 .ai_profile 的 type 欄位 ---
# content 類型專案隱藏 Docker/Test/Lint/Deploy targets
ASP_TYPE := $(shell grep '^type:' .ai_profile 2>/dev/null | awk '{print $$2}')

.PHONY: help \
        build clean deploy logs \
        test test-filter coverage lint i18n-check \
        diagram \
        adr-new adr-list \
        spec-new spec-list \
        postmortem-new postmortem-list \
        agent-done agent-status agent-reset agent-locks agent-unlock agent-lock-gc \
        session-checkpoint session-log \
        rag-index rag-search rag-stats rag-rebuild \
        guardrail-log guardrail-reset \
        audit-health audit-quick doc-audit tech-debt-list \
        task-start task-status task-report

#---------------------------------------------------------------------------
# Help
#---------------------------------------------------------------------------

help:
	@echo ""
	@echo "AI-SOP-Protocol 指令速查（type: $(or $(ASP_TYPE),未設定)）"
	@echo "========================="
	@echo ""
ifneq ($(ASP_TYPE),content)
	@echo "📦 Container:   build | clean | deploy | logs"
	@echo "🧪 Test:        test | test-filter FILTER=xxx | coverage | lint"
	@echo "🌐 i18n:        i18n-check"
	@echo "📐 Docs:        diagram"
endif
	@echo "📋 ADR:         adr-new TITLE=... | adr-list"
	@echo "📄 Spec:        spec-new TITLE=... | spec-list"
	@echo "🔥 Postmortem:  postmortem-new TITLE=... | postmortem-list"
	@echo "🤖 Agent:       agent-done TASK=... STATUS=... | agent-status | agent-reset | agent-unlock FILE=... | agent-lock-gc"
	@echo "💾 Session:     session-checkpoint NEXT=... | session-log"
	@echo "🧠 RAG:         rag-index | rag-search Q=... | rag-stats | rag-rebuild"
	@echo "🛡  Guardrail:   guardrail-log | guardrail-reset"
	@echo "🏥 Audit:       audit-health | audit-quick | doc-audit | tech-debt-list"
	@echo "📌 Task:        task-start DESC=... | task-status | task-report"
	@echo "🚀 Autopilot:   autopilot-init | autopilot-validate | autopilot-status | autopilot-reset"
	@echo "📝 Documents:   srs-new | sds-new | uiux-spec-new | deploy-spec-new"
	@echo ""

#---------------------------------------------------------------------------
# Docker / Container（type: content 時隱藏）
#---------------------------------------------------------------------------
ifneq ($(ASP_TYPE),content)

build:
	@echo "🔨 Building $(APP_NAME):$(VERSION)..."
	docker build -t $(APP_NAME):$(VERSION) .

clean:
	@echo "🧹 Cleaning..."
	rm -rf ./tmp/* 2>/dev/null || true
	docker-compose down --rmi local --volumes --remove-orphans 2>/dev/null || true
	docker rmi $$(docker images '$(APP_NAME)' -q) 2>/dev/null || true

deploy:
	@echo "🚀 Deploying $(APP_NAME):$(VERSION)..."
	docker-compose up -d --force-recreate
	docker-compose ps

logs:
	docker-compose logs -f --tail=100

#---------------------------------------------------------------------------
# Test（type: content 時隱藏）
#---------------------------------------------------------------------------

test:
	@echo "🧪 Running tests..."
	@if [ -f "go.mod" ]; then go test ./... -v -race -coverprofile=coverage.out; \
	elif command -v pytest >/dev/null 2>&1 && { [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -d "tests" ]; }; then pytest ./tests -v --cov=.; \
	elif [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then npm test; \
	else echo "⚠️  未偵測到測試框架（go.mod / pytest / package.json）"; exit 1; fi

test-filter:
	@if [ -z "$(FILTER)" ]; then echo "使用方式：make test-filter FILTER=xxx"; exit 1; fi
	@echo "🧪 Running filtered: $(FILTER)"
	@if [ -f "go.mod" ]; then go test ./... -run $(FILTER) -v; \
	elif command -v pytest >/dev/null 2>&1 && { [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -d "tests" ]; }; then pytest ./tests -k $(FILTER) -v; \
	elif [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then npm test -- --grep "$(FILTER)"; \
	else echo "⚠️  未偵測到測試框架"; exit 1; fi

coverage:
	@go tool cover -html=coverage.out 2>/dev/null || \
	coverage html && open htmlcov/index.html 2>/dev/null || \
	echo "⚠️  請先執行 make test"

lint:
	@echo "🔍 Linting..."
	@golangci-lint run ./... 2>/dev/null && exit 0 || true
	@flake8 . 2>/dev/null && exit 0 || true
	@npm run lint 2>/dev/null && exit 0 || true
	@echo "⚠️  未偵測到 Lint 工具"

#---------------------------------------------------------------------------
# i18n Check（type: content 時隱藏）
#---------------------------------------------------------------------------

i18n-check:
	@echo "🌐 Checking i18n consistency..."
	@LOCALE_DIR=$$(find . -maxdepth 4 -type d \( -name "locales" -o -name "i18n" -o -name "messages" -o -name "translations" -o -name "lang" \) ! -path '*/node_modules/*' ! -path '*/.git/*' | head -1); \
	if [ -z "$$LOCALE_DIR" ]; then \
		echo "⚠️  未偵測到語系目錄（locales/i18n/messages/translations/lang）"; \
		exit 0; \
	fi; \
	echo "  語系目錄：$$LOCALE_DIR"; \
	BASE_FILE=$$(ls $$LOCALE_DIR/*.json 2>/dev/null | head -1); \
	if [ -z "$$BASE_FILE" ]; then \
		echo "⚠️  語系目錄中未找到 JSON 檔案"; \
		exit 0; \
	fi; \
	BASE_COUNT=$$(python3 -c "import json; print(len(json.load(open('$$BASE_FILE'))))" 2>/dev/null || echo "ERR"); \
	if [ "$$BASE_COUNT" = "ERR" ]; then \
		echo "⚠️  無法解析 $$BASE_FILE（需要 python3）"; \
		exit 0; \
	fi; \
	echo "  基準檔案：$$BASE_FILE ($$BASE_COUNT keys)"; \
	FAIL=0; \
	for f in $$LOCALE_DIR/*.json; do \
		COUNT=$$(python3 -c "import json; print(len(json.load(open('$$f'))))" 2>/dev/null); \
		if [ "$$COUNT" != "$$BASE_COUNT" ]; then \
			echo "  ❌ $$f: $$COUNT keys (expected $$BASE_COUNT)"; \
			FAIL=1; \
		else \
			echo "  ✅ $$f: $$COUNT keys"; \
		fi; \
	done; \
	if [ "$$FAIL" = "1" ]; then \
		echo ""; \
		echo "❌ i18n key 數量不一致，請同步所有語系檔案"; \
		exit 1; \
	else \
		echo ""; \
		echo "✅ 所有語系檔案 key 數量一致"; \
	fi

#---------------------------------------------------------------------------
# Architecture Diagram（type: content 時隱藏）
#---------------------------------------------------------------------------

diagram:
	@echo "📐 Generating architecture diagram..."
	@# 從 architecture.md 提取 mermaid 區塊再餵給 mmdc
	@awk '/```mermaid/{flag=1;next}/```/{flag=0}flag' docs/architecture.md > /tmp/arch.mmd 2>/dev/null || true
	@mmdc -i /tmp/arch.mmd -o docs/architecture.png 2>/dev/null || \
	echo "⚠️  請安裝 mermaid-cli: npm install -g @mermaid-js/mermaid-cli"

else
# --- content 類型的 stub targets（避免 make: *** No rule to make target 錯誤）---
build clean deploy logs test test-filter coverage lint i18n-check diagram:
	@echo "⚠️  此指令不適用於 content 類型專案（目前 type: $(ASP_TYPE)）"
endif

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
# Postmortem
#---------------------------------------------------------------------------

postmortem-new:
	@if [ -z "$(TITLE)" ]; then read -p "Postmortem 標題: " TITLE; fi; \
	mkdir -p docs/postmortems; \
	COUNT=$$(ls docs/postmortems/PM-*.md 2>/dev/null | wc -l | tr -d ' '); \
	NUM=$$(printf "%03d" $$((COUNT + 1))); \
	SLUG=$$(echo "$(TITLE)" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-'); \
	FILE="docs/postmortems/PM-$$NUM-$$SLUG.md"; \
	cp .asp/templates/Postmortem_Template.md $$FILE; \
	SED_I=$$([ "$$(uname)" = "Darwin" ] && echo "sed -i ''" || echo "sed -i"); \
	$$SED_I "s/PM-000/PM-$$NUM/g" $$FILE; \
	$$SED_I "s/事件標題/$(TITLE)/g" $$FILE; \
	$$SED_I "s/YYYY-MM-DD/$$(date +%Y-%m-%d)/g" $$FILE; \
	echo "✅ 已建立: $$FILE"

postmortem-list:
	@echo "🔥 Postmortem 列表："; \
	ls docs/postmortems/PM-*.md 2>/dev/null | while read f; do \
		SEVERITY=$$(grep -m1 "嚴重等級" $$f | grep -o '`[^`]*`' | tr -d '`'); \
		TITLE=$$(head -1 $$f | sed 's/# //'); \
		echo "  $$TITLE [$$SEVERITY]"; \
	done || echo "  (無 Postmortem)"

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
	@echo "🔍 Building RAG index (incremental)..."
	@python3 .asp/scripts/rag/build_index.py \
		--source docs/ \
		--source .asp/profiles/ \
		--output .rag/index \
		--model all-MiniLM-L6-v2 \
		--incremental 2>/dev/null || \
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
# 專案健康審計
#---------------------------------------------------------------------------

audit-health:
	@echo ""
	@echo "🏥 專案健康審計（完整掃描）"
	@echo "================================="
	@echo ""
	@BLOCKERS=0; WARNINGS=0; INFOS=0; \
	\
	echo "── 1. 測試覆蓋 ──"; \
	SRC_COUNT=0; TEST_COUNT=0; \
	for ext in go ts tsx js jsx py java rb; do \
		SRC_COUNT=$$((SRC_COUNT + $$(find . -name "*.$$ext" ! -path '*/node_modules/*' ! -path '*/.git/*' ! -path '*/vendor/*' ! -path '*/.next/*' ! -name '*_test.*' ! -name '*.test.*' ! -name '*.spec.*' ! -name 'test_*' ! -path '*/test*/*' 2>/dev/null | wc -l))); \
		TEST_COUNT=$$((TEST_COUNT + $$(find . \( -name "*_test.$$ext" -o -name "*.test.$$ext" -o -name "*.spec.$$ext" -o -name "test_*.$$ext" \) ! -path '*/node_modules/*' ! -path '*/.git/*' 2>/dev/null | wc -l))); \
	done; \
	if [ $$SRC_COUNT -gt 0 ]; then \
		RATIO=$$(echo "scale=0; $$TEST_COUNT * 100 / $$SRC_COUNT" | bc 2>/dev/null || echo "?"); \
		echo "  Source files: $$SRC_COUNT | Test files: $$TEST_COUNT | Coverage ratio: $${RATIO}%"; \
		if [ $$TEST_COUNT -eq 0 ] && [ $$SRC_COUNT -gt 5 ]; then \
			echo "  🔴 BLOCKER: 專案有 $$SRC_COUNT 個 source files 但無任何測試"; \
			BLOCKERS=$$((BLOCKERS + 1)); \
		elif [ "$$RATIO" != "?" ] && [ $$RATIO -lt 30 ]; then \
			echo "  🟡 WARNING: 測試覆蓋率低於 30%"; \
			WARNINGS=$$((WARNINGS + 1)); \
		else \
			echo "  ✅ OK"; \
		fi; \
	else echo "  ⚪ 無 source files"; fi; \
	echo ""; \
	\
	echo "── 2. SPEC 覆蓋 ──"; \
	SPEC_COUNT=$$(ls docs/specs/SPEC-*.md 2>/dev/null | wc -l | tr -d ' '); \
	echo "  SPEC 數量: $$SPEC_COUNT"; \
	if [ $$SPEC_COUNT -eq 0 ] && [ $$SRC_COUNT -gt 5 ]; then \
		echo "  🟡 WARNING: 專案有代碼但無任何 SPEC"; \
		WARNINGS=$$((WARNINGS + 1)); \
	else echo "  ✅ OK"; fi; \
	echo ""; \
	\
	echo "── 3. ADR 覆蓋 ──"; \
	ADR_COUNT=$$(ls docs/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' '); \
	DRAFT_WITH_CODE=0; \
	for f in docs/adr/ADR-*.md; do \
		[ -f "$$f" ] || continue; \
		STATUS=$$(grep -m1 "狀態" "$$f" 2>/dev/null | grep -o '`[^`]*`' | tr -d '`'); \
		if [ "$$STATUS" = "Draft" ]; then \
			ADR_ID=$$(basename "$$f" .md | grep -o 'ADR-[0-9]*'); \
			if grep -r "$$ADR_ID" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" . >/dev/null 2>&1; then \
				echo "  🔴 BLOCKER: $$ADR_ID 狀態為 Draft 但已有實作代碼（鐵則違反）"; \
				BLOCKERS=$$((BLOCKERS + 1)); \
				DRAFT_WITH_CODE=$$((DRAFT_WITH_CODE + 1)); \
			fi; \
		fi; \
	done; \
	echo "  ADR 數量: $$ADR_COUNT"; \
	if [ $$DRAFT_WITH_CODE -eq 0 ]; then echo "  ✅ OK"; fi; \
	echo ""; \
	\
	echo "── 4. 文件完整性 ──"; \
	for doc in README.md CHANGELOG.md; do \
		if [ ! -f "$$doc" ]; then \
			echo "  🟡 WARNING: 缺少 $$doc"; \
			WARNINGS=$$((WARNINGS + 1)); \
		else echo "  ✅ $$doc exists"; fi; \
	done; \
	if [ ! -f "docs/architecture.md" ] && [ "$(ASP_TYPE)" != "content" ] && [ $$SRC_COUNT -gt 10 ]; then \
		echo "  🟡 WARNING: 缺少 docs/architecture.md（系統專案建議有架構文件）"; \
		WARNINGS=$$((WARNINGS + 1)); \
	fi; \
	echo ""; \
	\
	echo "── 5. 程式碼衛生 ──"; \
	DEP_COUNT=$$(grep -r "DEPRECATED\|@deprecated" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .next | wc -l | tr -d ' '); \
	TODO_NO_OWNER=$$(grep -rn "TODO[^(]" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .next | wc -l | tr -d ' '); \
	FIXME_COUNT=$$(grep -rn "FIXME" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .next | wc -l | tr -d ' '); \
	TECH_DEBT=$$(grep -rn "tech-debt:" . 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .asp/profiles | wc -l | tr -d ' '); \
	if [ $$DEP_COUNT -gt 0 ]; then echo "  🟡 WARNING: $$DEP_COUNT 個 DEPRECATED 標記待清理"; WARNINGS=$$((WARNINGS + 1)); fi; \
	if [ $$TODO_NO_OWNER -gt 0 ]; then echo "  🟡 WARNING: $$TODO_NO_OWNER 個 TODO 無 owner"; WARNINGS=$$((WARNINGS + 1)); fi; \
	if [ $$FIXME_COUNT -gt 0 ]; then echo "  🟢 INFO: $$FIXME_COUNT 個 FIXME"; INFOS=$$((INFOS + 1)); fi; \
	if [ $$TECH_DEBT -gt 0 ]; then echo "  🟢 INFO: $$TECH_DEBT 個 tech-debt 標記"; INFOS=$$((INFOS + 1)); fi; \
	if [ $$DEP_COUNT -eq 0 ] && [ $$TODO_NO_OWNER -eq 0 ]; then echo "  ✅ OK"; fi; \
	echo ""; \
	\
	echo "── 6. 依賴健康 ──"; \
	LOCK_OK=1; \
	if [ -f "package.json" ] && [ ! -f "package-lock.json" ] && [ ! -f "yarn.lock" ] && [ ! -f "pnpm-lock.yaml" ]; then \
		echo "  🟡 WARNING: 有 package.json 但無 lock file"; WARNINGS=$$((WARNINGS + 1)); LOCK_OK=0; \
	fi; \
	if [ -f "pyproject.toml" ] && [ ! -f "poetry.lock" ] && [ ! -f "requirements.txt" ]; then \
		echo "  🟡 WARNING: 有 pyproject.toml 但無 lock file"; WARNINGS=$$((WARNINGS + 1)); LOCK_OK=0; \
	fi; \
	if [ -f "go.mod" ] && [ ! -f "go.sum" ]; then \
		echo "  🟡 WARNING: 有 go.mod 但無 go.sum"; WARNINGS=$$((WARNINGS + 1)); LOCK_OK=0; \
	fi; \
	if [ $$LOCK_OK -eq 1 ]; then echo "  ✅ OK"; fi; \
	echo ""; \
	\
	echo "── 7. 文件新鮮度 ──"; \
	STALE=0; \
	for spec in docs/specs/SPEC-*.md; do \
		[ -f "$$spec" ] || continue; \
		IMPL=$$(grep -A5 "追溯性\|Traceability" "$$spec" 2>/dev/null | grep -oE '[a-zA-Z0-9_/.-]+\.(go|ts|py|java|js)' | head -5); \
		for impl_file in $$IMPL; do \
			if [ -f "$$impl_file" ]; then \
				SPEC_DATE=$$(git log -1 --format=%at -- "$$spec" 2>/dev/null || echo 0); \
				IMPL_DATE=$$(git log -1 --format=%at -- "$$impl_file" 2>/dev/null || echo 0); \
				if [ "$$IMPL_DATE" -gt "$$SPEC_DATE" ] 2>/dev/null; then \
					SPEC_NAME=$$(basename "$$spec"); \
					echo "  🟡 WARNING: $$SPEC_NAME 的實作檔案 $$impl_file 較新（doc-stale）"; \
					WARNINGS=$$((WARNINGS + 1)); \
					STALE=$$((STALE + 1)); \
				fi; \
			fi; \
		done; \
	done; \
	if [ $$STALE -eq 0 ]; then \
		SPEC_COUNT=$$(ls docs/specs/SPEC-*.md 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$SPEC_COUNT" -gt 0 ]; then \
			HAS_TRACE=$$(grep -rl "追溯性\|Traceability" docs/specs/SPEC-*.md 2>/dev/null | wc -l | tr -d ' '); \
			if [ "$$HAS_TRACE" = "0" ]; then \
				echo "  🟡 WARNING: $$SPEC_COUNT 個 SPEC 均無 Traceability 資料，無法驗證新鮮度"; \
				WARNINGS=$$((WARNINGS + 1)); \
			else \
				echo "  ✅ OK"; \
			fi; \
		else \
			echo "  ✅ OK（無 SPEC）"; \
		fi; \
	fi; \
	echo ""; \
	\
	echo "=================================" ; \
	echo "🏥 審計摘要：🔴 $$BLOCKERS blocker | 🟡 $$WARNINGS warning | 🟢 $$INFOS info"; \
	if [ $$BLOCKERS -gt 0 ]; then \
		echo "⚠️  有 blocker 需先修復才能開始主任務"; \
	fi; \
	echo ""

audit-quick:
	@echo "🏥 快速審計（僅 blocker）..."
	@BLOCKERS=0; \
	for f in docs/adr/ADR-*.md; do \
		[ -f "$$f" ] || continue; \
		STATUS=$$(grep -m1 "狀態" "$$f" 2>/dev/null | grep -o '`[^`]*`' | tr -d '`'); \
		if [ "$$STATUS" = "Draft" ]; then \
			ADR_ID=$$(basename "$$f" .md | grep -o 'ADR-[0-9]*'); \
			if grep -r "$$ADR_ID" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" . >/dev/null 2>&1; then \
				echo "  🔴 BLOCKER: $$ADR_ID Draft 但有實作代碼"; \
				BLOCKERS=$$((BLOCKERS + 1)); \
			fi; \
		fi; \
	done; \
	SRC_COUNT=$$(find . -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.java" | grep -v node_modules | grep -v .git | grep -v vendor | grep -v '.next' | wc -l); \
	TEST_COUNT=$$(find . \( -name "*_test.*" -o -name "*.test.*" -o -name "*.spec.*" -o -name "test_*" \) | grep -v node_modules | grep -v .git | grep -v '.next' | wc -l); \
	if [ $$TEST_COUNT -eq 0 ] && [ $$SRC_COUNT -gt 5 ]; then \
		echo "  🔴 BLOCKER: $$SRC_COUNT source files, 0 test files"; \
		BLOCKERS=$$((BLOCKERS + 1)); \
	fi; \
	if [ $$BLOCKERS -eq 0 ]; then echo "  ✅ 無 blocker"; fi

doc-audit:
	@echo "📄 文件新鮮度掃描..."
	@STALE=0; \
	for spec in docs/specs/SPEC-*.md; do \
		[ -f "$$spec" ] || continue; \
		IMPL=$$(grep -A5 "追溯性\|Traceability" "$$spec" 2>/dev/null | grep -oE '[a-zA-Z0-9_/.-]+\.(go|ts|py|java|js)' | head -5); \
		for impl_file in $$IMPL; do \
			if [ -f "$$impl_file" ]; then \
				SPEC_DATE=$$(git log -1 --format=%at -- "$$spec" 2>/dev/null || echo 0); \
				IMPL_DATE=$$(git log -1 --format=%at -- "$$impl_file" 2>/dev/null || echo 0); \
				if [ "$$IMPL_DATE" -gt "$$SPEC_DATE" ] 2>/dev/null; then \
					SPEC_NAME=$$(basename "$$spec"); \
					echo "  🟡 STALE: $$SPEC_NAME ← $$impl_file (impl newer)"; \
					STALE=$$((STALE + 1)); \
				fi; \
			fi; \
		done; \
	done; \
	if [ $$STALE -eq 0 ]; then echo "  ✅ 所有 SPEC 文件同步（或無 Traceability 資料）"; fi

tech-debt-list:
	@echo "🔧 Tech Debt 彙總"
	@echo "================================="
	@echo ""
	@echo "── tech-debt: 標記 ──"
	@grep -rn "tech-debt:" --include="*.go" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.java" --include="*.md" . 2>/dev/null | grep -v node_modules | grep -v .git | grep -v '.asp/profiles/' | grep -v '.asp/templates/' || echo "  (none)"
	@echo ""
	@echo "── TODO 無 owner ──"
	@grep -rn "TODO[^(]" --include="*.go" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.java" . 2>/dev/null | grep -v node_modules | grep -v .git || echo "  (none)"
	@echo ""
	@echo "── FIXME ──"
	@grep -rn "FIXME" --include="*.go" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.java" . 2>/dev/null | grep -v node_modules | grep -v .git || echo "  (none)"
	@echo ""
	@echo "── DEPRECATED ──"
	@grep -rn "DEPRECATED\|@deprecated" --include="*.go" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.java" . 2>/dev/null | grep -v node_modules | grep -v .git || echo "  (none)"
	@echo ""

#---------------------------------------------------------------------------
# 任務協調
#---------------------------------------------------------------------------

task-start:
	@if [ -z "$(DESC)" ]; then echo "使用方式：make task-start DESC=\"任務描述\""; exit 1; fi
	@mkdir -p docs
	@echo "{\"desc\":\"$(DESC)\",\"ts\":\"$$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"started\"}" \
		>> docs/task-log.jsonl
	@echo "📌 任務已記錄：$(DESC)"

task-status:
	@echo "📋 最近任務："
	@if [ -f docs/task-log.jsonl ]; then \
		tail -10 docs/task-log.jsonl | python3 -c "import sys,json; \
[print(f'  [{l[\"status\"]}] {l[\"desc\"][:60]} @ {l[\"ts\"]}') \
for l in (json.loads(x) for x in sys.stdin)]" 2>/dev/null || \
		tail -10 docs/task-log.jsonl; \
	else echo "  (無任務紀錄)"; fi

task-report:
	@echo "📊 任務統計："
	@if [ -f docs/task-log.jsonl ]; then \
		python3 -c "import json; \
tasks=[json.loads(l) for l in open('docs/task-log.jsonl')]; \
total=len(tasks); \
started=sum(1 for t in tasks if t.get('status')=='started'); \
completed=sum(1 for t in tasks if t.get('status')=='completed'); \
print(f'  Total: {total} | Started: {started} | Completed: {completed}')" 2>/dev/null; \
	else echo "  (無任務紀錄)"; fi

#---------------------------------------------------------------------------
# Autopilot
#---------------------------------------------------------------------------

autopilot-init:
	@if [ -f "ROADMAP.yaml" ]; then \
		echo "⚠️  ROADMAP.yaml already exists"; \
	else \
		cp .asp/templates/ROADMAP_Template.yaml ROADMAP.yaml; \
		echo "✅ Created ROADMAP.yaml from template"; \
	fi

autopilot-validate:
	@echo "🔍 Validating ROADMAP.yaml..."
	@python3 -c '\
import yaml, sys, os;\
data = yaml.safe_load(open("ROADMAP.yaml"));\
tasks = [t for m in data.get("milestones",[]) for t in m.get("tasks",[])];\
ids = [t["id"] for t in tasks];\
errors = [];\
[errors.append(t["id"]+" depends on unknown "+d) for t in tasks for d in (t.get("depends_on") or []) if d not in ids];\
[errors.append(t["id"]+" references missing "+t["adr"]) for t in tasks if t.get("adr") and not any(t["adr"] in f for f in (os.listdir("docs/adr") if os.path.isdir("docs/adr") else []))];\
docs = data.get("documents",{});\
[errors.append("Document "+k+": "+v+" not found") for k,v in docs.items() if v and not os.path.exists(v)];\
pending = sum(1 for t in tasks if t.get("status")=="pending");\
print("  Tasks: "+str(len(tasks))+" | Pending: "+str(pending)+" | Errors: "+str(len(errors)));\
[print("  \u274c "+e) for e in errors];\
sys.exit(1 if errors else 0)'
	@echo "📝 Updating CLAUDE.md project description..."
	@python3 .asp/scripts/update-project-description.py

autopilot-status:
	@echo "🤖 Autopilot Status"
	@echo "==================="
	@if [ -f ".asp-autopilot-state.json" ]; then \
		python3 -c '\
import json; s=json.load(open(".asp-autopilot-state.json"));\
print("  Status:    "+s["status"]);\
print("  Sessions:  "+str(s["session_count"]));\
print("  Current:   "+s.get("current_task","N/A"));\
print("  Completed: "+str(len(s["completed"]))+"/"+str(s.get("total_tasks","?")));\
print("  Failed:    "+str(len(s.get("failed",[]))));\
print("  Blocked:   "+str(len(s.get("blocked",[]))));\
print("  Exit:      "+s.get("exit_reason","N/A"))'; \
	else echo "  (No autopilot state — not started)"; fi
	@echo ""
	@if [ -f "ROADMAP.yaml" ]; then \
		python3 -c '\
import yaml; data=yaml.safe_load(open("ROADMAP.yaml"));\
tasks=[t for m in data.get("milestones",[]) for t in m.get("tasks",[])];\
by_status={};\
[by_status.setdefault(t.get("status","pending"),[]).append(t["id"]) for t in tasks];\
print("  ROADMAP progress:");\
[print("    "+s+": "+str(len(by_status[s]))) for s in ["completed","in_progress","pending","blocked","failed","skipped"] if s in by_status]'; \
	else echo "  (No ROADMAP.yaml)"; fi

autopilot-reset:
	@rm -f .asp-autopilot-state.json
	@echo "🧹 Autopilot state cleared (ROADMAP.yaml unchanged)"

srs-new:
	@mkdir -p docs
	@if [ ! -f "docs/SRS.md" ]; then \
		cp .asp/templates/SRS_Template.md docs/SRS.md; \
		echo "✅ Created docs/SRS.md from template"; \
	else echo "ℹ️  docs/SRS.md already exists"; fi

sds-new:
	@mkdir -p docs
	@if [ ! -f "docs/SDS.md" ]; then \
		cp .asp/templates/SDS_Template.md docs/SDS.md; \
		echo "✅ Created docs/SDS.md from template"; \
	else echo "ℹ️  docs/SDS.md already exists"; fi

uiux-spec-new:
	@mkdir -p docs
	@if [ ! -f "docs/UIUX_SPEC.md" ]; then \
		cp .asp/templates/UIUX_SPEC_Template.md docs/UIUX_SPEC.md; \
		echo "✅ Created docs/UIUX_SPEC.md from template"; \
	else echo "ℹ️  docs/UIUX_SPEC.md already exists"; fi

deploy-spec-new:
	@mkdir -p docs
	@if [ ! -f "docs/DEPLOY_SPEC.md" ]; then \
		cp .asp/templates/DEPLOY_SPEC_Template.md docs/DEPLOY_SPEC.md; \
		echo "✅ Created docs/DEPLOY_SPEC.md from template"; \
	else echo "ℹ️  docs/DEPLOY_SPEC.md already exists"; fi
