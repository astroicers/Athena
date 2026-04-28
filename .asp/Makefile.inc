# AI-SOP-Protocol — ASP Targets (included by project Makefile)
# 勿直接編輯此檔案，升級 ASP 時會自動覆蓋
# ASP_MAKEFILE_VERSION=3.4.0

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
        task-start task-status task-report \
        profile-validate \
        agent-memory-init agent-session-init audit-baseline-init \
        asp-unlock-commit asp-refresh asp-enforcement-status \
        runbook-list runbook-view

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
	@echo "🤖 Agent v3:    agent-handoff-list | agent-tracks | agent-escalation-log | agent-memory-show | agent-team-recommend TYPE=..."
	@echo "🤖 Agent Init:  agent-memory-init | agent-session-init | audit-baseline-init"
	@echo "💾 Session:     session-checkpoint NEXT=... | session-log"
	@echo "🧠 RAG:         rag-index | rag-search Q=... | rag-stats | rag-rebuild"
	@echo "🛡  Guardrail:   guardrail-log | guardrail-reset"
	@echo "🏥 Audit:       audit-health | audit-quick | doc-audit | tech-debt-list"
	@echo "🔒 Enforce:     asp-unlock-commit | asp-refresh | asp-enforcement-status"
	@echo "📌 Task:        task-start DESC=... | task-status | task-report"
	@echo "🔍 Profile:     profile-validate"
	@echo "🚀 Autopilot:   autopilot-init | autopilot-validate | autopilot-status | autopilot-reset"
	@echo "📝 Documents:   srs-new | sds-new | uiux-spec-new | deploy-spec-new"
	@echo "📚 Runbook:     runbook-list | runbook-view SCENARIO=..."
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
# Runbooks
#---------------------------------------------------------------------------

runbook-list: ## 列出可用的場景 Runbook
	@echo "📚 Runbook 列表（docs/runbooks/）："; \
	ls docs/runbooks/*.md 2>/dev/null | while read f; do \
		TITLE=$$(head -1 $$f | sed 's/# //'); \
		MODE=$$(grep -m1 '^\*\*模式\*\*' $$f | sed 's/.*：//;s/ |.*//' | tr -d ' '); \
		echo "  $$(basename $$f .md)  $$TITLE"; \
	done || echo "  (無 Runbook)"

runbook-view: ## 檢視 Runbook (SCENARIO=startup-mvp|incident-response|enterprise-feature)
	@if [ -z "$(SCENARIO)" ]; then echo "用法: make runbook-view SCENARIO=startup-mvp"; exit 1; fi
	@FILE="docs/runbooks/$(SCENARIO).md"; \
	if [ ! -f "$$FILE" ]; then echo "❌ 找不到 $$FILE。可用場景："; make runbook-list; exit 1; fi; \
	cat "$$FILE"

#---------------------------------------------------------------------------
# Multi-Agent
#---------------------------------------------------------------------------

agent-done: ## Worker 完成回報 (TASK=xxx STATUS=success|failed [REASON=...])
	@if [ -z "$(TASK)" ] || [ -z "$(STATUS)" ]; then echo "用法: make agent-done TASK=TASK-001 STATUS=success [REASON=...]"; exit 1; fi
	@mkdir -p .agent-events .agent-events/handoffs
	@TS=$$(date -u +%Y-%m-%dT%H:%M:%SZ); \
	SEQ=$$(date +%Y%m%d-%H%M%S); \
	echo "{\"task\":\"$(TASK)\",\"status\":\"$(STATUS)\",\"ts\":\"$$TS\",\"reason\":\"$(REASON)\"}" >> .agent-events/completed.jsonl; \
	HID="HANDOFF-$$SEQ"; \
	printf "handoff_type: TASK_COMPLETE\ntask_id: \"%s\"\ntimestamp: \"%s\"\nstatus: \"%s\"\nreason: \"%s\"\n" "$(TASK)" "$$TS" "$(STATUS)" "$(REASON)" > ".agent-events/handoffs/$$HID.yaml"; \
	echo "{\"id\":\"$$HID\",\"type\":\"TASK_COMPLETE\",\"task\":\"$(TASK)\",\"status\":\"$(STATUS)\",\"ts\":\"$$TS\"}" >> .agent-events/handoffs/index.jsonl; \
	echo "✅ $(TASK) $(STATUS) — $$HID"

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

# ─── Agent Handoff（v3.0）───────────────────────────────────────────
.PHONY: agent-handoff-list agent-handoff-view agent-tracks agent-track-status agent-escalation-log agent-memory-show agent-memory-prune agent-team-recommend

agent-handoff-list: ## 列出所有交接單
	@echo "═══ Agent Handoffs ═══"
	@if [ -f .agent-events/handoffs/index.jsonl ]; then \
		cat .agent-events/handoffs/index.jsonl | tail -20; \
	else \
		echo "  (無交接單)"; \
	fi

agent-handoff-view: ## 檢視交接單 (ID=HANDOFF-xxx)
	@if [ -z "$(ID)" ]; then echo "用法: make agent-handoff-view ID=HANDOFF-xxx"; exit 1; fi
	@if [ -f ".agent-events/handoffs/$(ID).yaml" ]; then \
		cat ".agent-events/handoffs/$(ID).yaml"; \
	else \
		echo "交接單不存在: $(ID)"; exit 1; \
	fi

agent-tracks: ## 顯示當前並行軌道狀態
	@echo "═══ Parallel Tracks ═══"
	@if [ -f .asp-agent-session.json ]; then \
		python3 -c "import json; d=json.load(open('.asp-agent-session.json')); \
		[print(f\"  Track {t['id']}: {t['status']} (task: {t['task']}, agent: {t['agent']})\") for t in d.get('active_tracks',[])]" 2>/dev/null \
		|| echo "  (無法讀取 session 狀態)"; \
	else \
		echo "  (無活躍 session)"; \
	fi

agent-track-status: ## 特定軌道詳情 (TRACK=A)
	@if [ -z "$(TRACK)" ]; then echo "用法: make agent-track-status TRACK=A"; exit 1; fi
	@if [ -f .asp-agent-session.json ]; then \
		python3 -c "import json; d=json.load(open('.asp-agent-session.json')); \
		tracks=[t for t in d.get('active_tracks',[]) if t['id']=='$(TRACK)']; \
		print(json.dumps(tracks[0],indent=2,ensure_ascii=False)) if tracks else print('Track $(TRACK) 不存在')" 2>/dev/null; \
	else \
		echo "  (無活躍 session)"; \
	fi

agent-escalation-log: ## 顯示升級歷史
	@echo "═══ Escalation Log ═══"
	@find .agent-events/handoffs/ -name "*.yaml" -exec grep -l "handoff_type: ESCALATION" {} \; 2>/dev/null \
		| while read f; do \
			echo "---"; \
			grep -E "^(severity|task_id|reason|timestamp):" "$$f"; \
		done || echo "  (無升級記錄)"

agent-memory-show: ## 顯示 Agent 學習記憶
	@echo "═══ Agent Memory ═══"
	@if [ -f .asp-agent-memory.yaml ]; then \
		cat .asp-agent-memory.yaml; \
	else \
		echo "  (無記憶——首次執行)"; \
	fi

agent-memory-prune: ## 修剪過期記憶 (AGE=90 天)
	@echo "修剪超過 $(or $(AGE),90) 天的記憶..."
	@if [ -f .asp-agent-memory.yaml ]; then \
		python3 -c " \
import sys, yaml, datetime; \
age = int(sys.argv[1]); \
d = yaml.safe_load(open('.asp-agent-memory.yaml')) or {}; \
now = datetime.datetime.now(); \
cutoff = now - datetime.timedelta(days=age); \
for key in ['fix_strategies', 'common_failures']: \
    if key in d: \
        before = len(d[key]); \
        d[key] = [x for x in d[key] if datetime.datetime.fromisoformat(x.get('last_used', x.get('last_occurrence', now.isoformat()))[:10]) >= cutoff]; \
        print(f'  {key}: {before} → {len(d[key])}'); \
yaml.dump(d, open('.asp-agent-memory.yaml', 'w'), allow_unicode=True)" "$(or $(AGE),90)" 2>/dev/null \
		|| echo "  (修剪失敗——需要 PyYAML)"; \
	else \
		echo "  (無記憶可修剪)"; \
	fi

agent-team-recommend: ## 推薦團隊組成 (TYPE=NEW_FEATURE COMPLEXITY=simple|complex)
	@if [ -z "$(TYPE)" ]; then echo "用法: make agent-team-recommend TYPE=NEW_FEATURE COMPLEXITY=simple"; exit 1; fi
	@SCENARIO="$(TYPE)_$(COMPLEXITY)"; \
	if [ -f .asp/agents/team_compositions.yaml ]; then \
		echo "═══ Team Recommendation: $$SCENARIO ═══"; \
		python3 -c " \
import yaml; \
d = yaml.safe_load(open('.asp/agents/team_compositions.yaml')); \
s = d.get('scenarios',{}).get('$$SCENARIO'); \
if s: \
    print(f\"  場景: $$SCENARIO\"); \
    print(f\"  說明: {s.get('description','')}\"); \
    print(f\"  角色: {', '.join(s.get('agents',[]))}\"); \
    print(f\"  管線: {', '.join(s.get('pipeline_phases',[]))}\"); \
    print(f\"  並行: {'是' if s.get('parallel') else '否'}\"); \
else: \
    print(f'場景 $$SCENARIO 不存在。可用場景:'); \
    [print(f'  - {k}') for k in d.get('scenarios',{}).keys()]" 2>/dev/null \
		|| echo "  (需要 PyYAML)"; \
	else \
		echo "  (team_compositions.yaml 不存在)"; \
	fi

# ─── Agent Init（v3.3）───────────────────────────────────────────
agent-memory-init: ## 初始化 Agent Memory
	@if [ -f .asp-agent-memory.yaml ]; then \
		echo "⚠️ .asp-agent-memory.yaml 已存在，跳過"; \
	else \
		printf "version: 1\nfix_strategies: []\ncommon_failures: []\nteam_effectiveness: []\n" > .asp-agent-memory.yaml; \
		echo "✅ .asp-agent-memory.yaml 已建立"; \
		grep -q "asp-agent-memory.yaml" .gitignore 2>/dev/null || echo ".asp-agent-memory.yaml" >> .gitignore; \
	fi

agent-session-init: ## 初始化 Agent Session
	@printf '{"session_id":"session-%s","started_at":"%s","team_composition":{},"active_tracks":[],"pending_handoffs":[],"current_pipeline_phase":null,"last_gate_passed":null,"escalations":[]}\n' "$$(date +%Y%m%d-%H%M%S)" "$$(date -u +%Y-%m-%dT%H:%M:%SZ)" | python3 -m json.tool > .asp-agent-session.json 2>/dev/null || echo '{}' > .asp-agent-session.json
	@echo "✅ .asp-agent-session.json 已建立"
	@grep -q "asp-agent-session.json" .gitignore 2>/dev/null || echo ".asp-agent-session.json" >> .gitignore

audit-baseline-init: ## 初始化審計基線
	@echo "🏥 建立審計基線..."
	@SRC=$$(find . -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.java" -o -name "*.js" 2>/dev/null | grep -v node_modules | grep -v .git | grep -v vendor | grep -v '_test\.' | grep -v '.test\.' | grep -v '.spec\.' | grep -v 'test_' | wc -l | tr -d ' '); \
	TST=$$(find . \( -name "*_test.*" -o -name "*.test.*" -o -name "*.spec.*" -o -name "test_*" \) 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '); \
	SPC=$$(ls docs/specs/SPEC-*.md 2>/dev/null | wc -l | tr -d ' '); \
	ADR=$$(ls docs/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' '); \
	TD=$$(grep -rn "TODO[^(]\|FIXME" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '); \
	if [ $$SRC -gt 0 ]; then R=$$(echo "scale=2; $$TST / $$SRC" | bc 2>/dev/null || echo "0"); else R="0"; fi; \
	printf '{"last_audit":"%s","test_coverage_ratio":%s,"spec_count":%s,"adr_count":%s,"blockers":0,"warnings":0,"info":0,"lint_warning_count":0,"todo_fixme_count":%s,"side_effects_unverified":0,"rollback_untested_count":0}\n' \
		"$$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$R" "$$SPC" "$$ADR" "$$TD" | python3 -m json.tool > .asp-audit-baseline.json 2>/dev/null; \
	echo "✅ .asp-audit-baseline.json 已建立"; \
	cat .asp-audit-baseline.json
	@grep -q "asp-audit-baseline.json" .gitignore 2>/dev/null || echo ".asp-audit-baseline.json" >> .gitignore

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
# 強制力管理（Enforcement）
#---------------------------------------------------------------------------

asp-unlock-commit: ## 解除動態 commit 阻擋（修復 ADR/測試問題後使用）
	@SETTINGS=".claude/settings.json"; \
	if [ ! -f "$$SETTINGS" ]; then echo "❌ $$SETTINGS 不存在"; exit 1; fi; \
	BEFORE=$$(jq '.permissions.deny | length' "$$SETTINGS"); \
	jq '.permissions.deny = [.permissions.deny[]? | select(test("git commit") | not)]' \
		"$$SETTINGS" > "$${SETTINGS}.tmp" && mv "$${SETTINGS}.tmp" "$$SETTINGS"; \
	AFTER=$$(jq '.permissions.deny | length' "$$SETTINGS"); \
	echo "🔓 動態 deny 已解除（deny rules: $$BEFORE → $$AFTER）"; \
	echo "   ⚠️  下次 session 啟動時會重新評估"

asp-refresh: ## 重新執行 session 審計（修復問題後使用）
	@echo "🔄 重新執行 session 審計..."; \
	CLAUDE_PROJECT_DIR="$$(pwd)" bash .asp/hooks/clean-allow-list.sh 2>&1; \
	CLAUDE_PROJECT_DIR="$$(pwd)" bash .asp/hooks/session-audit.sh 2>&1; \
	echo ""; \
	echo "✅ 審計完成，briefing 已更新"

asp-enforcement-status: ## 顯示當前強制力狀態
	@echo ""; \
	echo "🔒 ASP 強制力狀態"; \
	echo "================================="; \
	echo ""; \
	echo "── Deny List（硬性阻擋）──"; \
	if [ -f ".claude/settings.json" ]; then \
		jq -r '.permissions.deny[]?' ".claude/settings.json" | while read -r rule; do \
			echo "  🚫 $$rule"; \
		done; \
	fi; \
	echo ""; \
	echo "── Session Briefing ──"; \
	if [ -f ".asp-session-briefing.json" ]; then \
		BLOCKERS=$$(jq '.blockers | length' ".asp-session-briefing.json"); \
		WARNS=$$(jq '.warnings | length' ".asp-session-briefing.json"); \
		DYNCOUNT=$$(jq '.dynamic_deny | length' ".asp-session-briefing.json"); \
		echo "  Blockers: $$BLOCKERS | Warnings: $$WARNS | Dynamic deny: $$DYNCOUNT patterns"; \
		if [ "$$BLOCKERS" -gt 0 ]; then \
			jq -r '.blockers[]' ".asp-session-briefing.json" | while read -r b; do \
				echo "  🔴 $$b"; \
			done; \
		fi; \
	else \
		echo "  (尚未執行 session 審計)"; \
	fi; \
	echo ""; \
	echo "── Gate State ──"; \
	if [ -f ".asp-gate-state.json" ]; then \
		jq -r '.gates | to_entries[] | "  \(.key): \(.value.status)"' ".asp-gate-state.json"; \
	else \
		echo "  (尚未初始化)"; \
	fi; \
	echo ""; \
	echo "── Bypass Log（近 7 天）──"; \
	if [ -f ".asp-bypass-log.json" ]; then \
		TOTAL=$$(jq 'length' ".asp-bypass-log.json" 2>/dev/null || echo 0); \
		RECENT=$$(jq --arg d "$$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" \
			'[.[] | select(.timestamp >= $$d)] | length' ".asp-bypass-log.json" 2>/dev/null || echo 0); \
		echo "  Total: $$TOTAL | Last 7 days: $$RECENT （檢視：make asp-bypass-review）"; \
	else \
		echo "  (無記錄)"; \
	fi; \
	echo ""

asp-bypass-review: ## 檢視 bypass 記錄（AI 繞過 skill 的歷史）
	@if [ ! -f ".asp-bypass-log.json" ]; then \
		echo "📋 .asp-bypass-log.json 不存在 — 尚未有任何 bypass 記錄"; \
		exit 0; \
	fi; \
	TOTAL=$$(jq 'length' ".asp-bypass-log.json"); \
	echo ""; \
	echo "📋 ASP Bypass Log"; \
	echo "================================="; \
	echo "Total entries: $$TOTAL"; \
	echo ""; \
	LIMIT=$${LIMIT:-20}; \
	echo "── 最近 $$LIMIT 筆 ──"; \
	jq -r ".[-$$LIMIT:] | reverse | .[] | \
		\"[\(.timestamp)] \(.skill) / \(.step)\n  reason: \(.reason)\n  actor: \(.actor // \"unknown\")\n\"" \
		".asp-bypass-log.json" 2>/dev/null || echo "  (jq 解析失敗 — 檔案可能損壞)"; \
	echo ""; \
	echo "── 按 skill 分組 ──"; \
	jq -r 'group_by(.skill) | .[] | "  \(.[0].skill): \(length) 次"' ".asp-bypass-log.json"; \
	echo ""; \
	echo "💡 若某 skill bypass 次數過高，考慮：(1) 補強 skill 文件 (2) 在 CLAUDE.md 加入對應鐵則"

asp-level-check: ## 檢查當前 ASP 成熟度等級與 graduation 進度
	@LEVEL=$$(grep -E '^level:' .ai_profile 2>/dev/null | awk '{print $$2}'); \
	if [ -z "$$LEVEL" ]; then \
		echo "⚠️  .ai_profile 無 level 欄位 — 使用 Level 推斷規則"; \
		if grep -q 'autopilot: enabled\|autonomous: enabled' .ai_profile 2>/dev/null; then LEVEL=5; \
		elif grep -q 'mode: multi-agent' .ai_profile 2>/dev/null; then LEVEL=4; \
		elif grep -q 'openapi: enabled' .ai_profile 2>/dev/null; then LEVEL=3; \
		elif grep -q 'guardrail: enabled\|coding_style: enabled' .ai_profile 2>/dev/null; then LEVEL=2; \
		else LEVEL=1; fi; \
		echo "   推斷等級：L$$LEVEL（建議在 .ai_profile 中補上 \`level: $$LEVEL\`）"; \
	fi; \
	LEVEL_FILE=".asp/levels/level-$$LEVEL.yaml"; \
	if [ ! -f "$$LEVEL_FILE" ]; then echo "❌ $$LEVEL_FILE 不存在"; exit 1; fi; \
	echo ""; \
	echo "🎯 ASP Level Check"; \
	echo "=================="; \
	echo ""; \
	NAME=$$(grep -E '^name:' "$$LEVEL_FILE" | head -1 | sed 's/name: *//'); \
	TAGLINE=$$(grep -E '^tagline:' "$$LEVEL_FILE" | sed 's/tagline: *//'); \
	echo "Current: L$$LEVEL ($$NAME)"; \
	echo "         $$TAGLINE"; \
	echo ""; \
	echo "已啟用 profile (從 .asp/levels/level-$$LEVEL.yaml)："; \
	awk '/^profiles:/{flag=1; next} /^[a-z]/{flag=0} flag && /^  -/{print "  "$$0}' "$$LEVEL_FILE"; \
	echo ""; \
	NEXT_LEVEL=$$(grep -E '^next_level:' "$$LEVEL_FILE" | awk '{print $$2}'); \
	if [ "$$NEXT_LEVEL" = "null" ] || [ -z "$$NEXT_LEVEL" ]; then \
		echo "✅ 已在最高等級 (L5)"; \
	else \
		NEXT_FILE=".asp/levels/level-$$NEXT_LEVEL.yaml"; \
		NEXT_NAME=$$(grep -E '^name:' "$$NEXT_FILE" | head -1 | sed 's/name: *//'); \
		echo "Next Level: L$$NEXT_LEVEL ($$NEXT_NAME)"; \
		echo ""; \
		echo "📋 L$$LEVEL Graduation Checklist（shell 可驗證的項目）："; \
		awk '/^graduation_checklist:/{flag=1; next} /^[a-z]/{flag=0} flag' "$$LEVEL_FILE" | \
			awk '/- id:/{id=$$3} /description:/{desc=$$0; sub(/[^"]*"/,"",desc); sub(/".*/,"",desc); print "  ["id"] "desc}'; \
		echo ""; \
		echo "💡 執行 skill /asp-level 獲得逐項驗證與升級建議"; \
	fi; \
	echo ""

asp-level-upgrade: ## 升級到下一個 ASP 等級（需先通過 asp-level-check）
	@CURRENT=$$(grep -E '^level:' .ai_profile 2>/dev/null | awk '{print $$2}'); \
	if [ -z "$$CURRENT" ]; then echo "❌ .ai_profile 無 level 欄位，先執行 make asp-level-check"; exit 1; fi; \
	LEVEL_FILE=".asp/levels/level-$$CURRENT.yaml"; \
	NEXT=$$(grep -E '^next_level:' "$$LEVEL_FILE" | awk '{print $$2}'); \
	if [ "$$NEXT" = "null" ] || [ -z "$$NEXT" ]; then echo "✅ 已在最高等級 (L$$CURRENT)"; exit 0; fi; \
	NEXT_FILE=".asp/levels/level-$$NEXT.yaml"; \
	if [ ! -f "$$NEXT_FILE" ]; then echo "❌ $$NEXT_FILE 不存在"; exit 1; fi; \
	NEXT_NAME=$$(grep -E '^name:' "$$NEXT_FILE" | head -1 | sed 's/name: *//'); \
	echo "🚀 升級 L$$CURRENT → L$$NEXT ($$NEXT_NAME)"; \
	echo ""; \
	cp .ai_profile ".ai_profile.backup-L$$CURRENT"; \
	echo "✅ 已備份 .ai_profile → .ai_profile.backup-L$$CURRENT"; \
	echo ""; \
	echo "📋 請用 skill /asp-level 完成以下步驟："; \
	echo "   1. 根據 $$NEXT_FILE 的 ai_profile_hint 更新 .ai_profile"; \
	echo "   2. 執行 make asp-refresh"; \
	echo "   3. 跑 make asp-level-check 確認新等級"

asp-level-list: ## 列出所有 ASP 等級
	@echo ""; \
	echo "🎯 ASP Maturity Levels"; \
	echo "======================"; \
	for f in .asp/levels/level-*.yaml; do \
		if [ -f "$$f" ]; then \
			LV=$$(grep -E '^level:' "$$f" | awk '{print $$2}'); \
			NM=$$(grep -E '^name:' "$$f" | head -1 | sed 's/name: *//'); \
			TG=$$(grep -E '^tagline:' "$$f" | sed 's/tagline: *//'); \
			echo "  L$$LV  $$NM — $$TG"; \
		fi; \
	done; \
	echo ""; \
	echo "詳細資訊：cat .asp/levels/level-N.yaml"; \
	echo "等級檢查：make asp-level-check"

asp-bypass-record: ## 寫入 bypass 記錄（內部使用，或手動記錄：SKILL=asp-ship STEP=5 REASON="..."）
	@if [ -z "$(SKILL)" ] || [ -z "$(STEP)" ] || [ -z "$(REASON)" ]; then \
		echo "❌ 用法：make asp-bypass-record SKILL=asp-ship STEP=Step5 REASON=\"...\" [ACTOR=ai|user]"; \
		exit 1; \
	fi; \
	ACTOR="$${ACTOR:-ai}"; \
	TS=$$(date -u +%Y-%m-%dT%H:%M:%SZ); \
	ENTRY=$$(jq -n --arg t "$$TS" --arg s "$(SKILL)" --arg st "$(STEP)" --arg r "$(REASON)" --arg a "$$ACTOR" \
		'{timestamp:$$t, skill:$$s, step:$$st, reason:$$r, actor:$$a}'); \
	if [ ! -f ".asp-bypass-log.json" ]; then echo "[]" > ".asp-bypass-log.json"; fi; \
	jq ". + [$$ENTRY]" ".asp-bypass-log.json" > ".asp-bypass-log.json.tmp" && \
		mv ".asp-bypass-log.json.tmp" ".asp-bypass-log.json"; \
	echo "✅ Bypass 記錄已寫入 (.asp-bypass-log.json)"

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
		SRC_COUNT=$$((SRC_COUNT + $$(find . -name "*.$$ext" ! -path '*/node_modules/*' ! -path '*/.git/*' ! -path '*/vendor/*' ! -name '*_test.*' ! -name '*.test.*' ! -name '*.spec.*' ! -name 'test_*' ! -path '*/test*/*' 2>/dev/null | wc -l))); \
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
	echo "── 1c. E2E 測試（全端專案）──"; \
	HAS_FE=0; HAS_BE=0; \
	[ -d "frontend" ] && HAS_FE=1; \
	([ -d "backend" ] || [ -d "api" ] || [ -d "server" ]) && HAS_BE=1; \
	if [ $$HAS_FE -eq 1 ] && [ $$HAS_BE -eq 1 ]; then \
		if [ ! -f "playwright.config.ts" ] && [ ! -f "playwright.config.js" ]; then \
			echo "  🔴 BLOCKER: 全端專案缺少 Playwright 設定"; \
			BLOCKERS=$$((BLOCKERS + 1)); \
		else \
			E2E_DIR=""; \
			for d in e2e tests/e2e frontend/e2e; do [ -d "$$d" ] && E2E_DIR="$$d" && break; done; \
			if [ -z "$$E2E_DIR" ]; then \
				echo "  🔴 BLOCKER: 全端專案缺少 E2E 測試目錄"; \
				BLOCKERS=$$((BLOCKERS + 1)); \
			else \
				E2E_N=$$(find "$$E2E_DIR" \( -name "*.spec.ts" -o -name "*.e2e.ts" -o -name "*.test.ts" \) 2>/dev/null | wc -l | tr -d ' '); \
				if [ $$E2E_N -eq 0 ]; then echo "  🔴 BLOCKER: E2E 目錄存在但無測試"; BLOCKERS=$$((BLOCKERS + 1)); \
				elif [ $$E2E_N -lt 3 ]; then echo "  🟡 WARNING: E2E 僅 $$E2E_N 個（建議 ≥ 3）"; WARNINGS=$$((WARNINGS + 1)); \
				else echo "  ✅ E2E 測試 $$E2E_N 個"; fi; \
			fi; \
		fi; \
	else echo "  ⚪ 非全端專案，跳過"; fi; \
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
	DEP_COUNT=$$(grep -r "DEPRECATED\|@deprecated" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '); \
	TODO_NO_OWNER=$$(grep -rn "TODO[^(]" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '); \
	FIXME_COUNT=$$(grep -rn "FIXME" --include="*.go" --include="*.ts" --include="*.py" --include="*.java" --include="*.js" . 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '); \
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
	echo "── 8. 測試品質（v3.3）──"; \
	EMPTY_TESTS=0; \
	for ext in go ts js py java; do \
		for tf in $$(find . \( -name "*_test.$$ext" -o -name "*.test.$$ext" -o -name "*.spec.$$ext" \) ! -path '*/node_modules/*' ! -path '*/.git/*' 2>/dev/null); do \
			case $$ext in \
				go) A=$$(grep -c "assert\|require\.\|t\.Error\|t\.Fatal" "$$tf" 2>/dev/null || echo 0);; \
				py) A=$$(grep -c "assert\|assertEqual\|assertTrue" "$$tf" 2>/dev/null || echo 0);; \
				ts|js) A=$$(grep -c "expect(\|assert\." "$$tf" 2>/dev/null || echo 0);; \
				java) A=$$(grep -c "assert\|assertEquals" "$$tf" 2>/dev/null || echo 0);; \
				*) A=1;; \
			esac; \
			if [ "$$A" = "0" ]; then \
				echo "  🟡 WARNING: $$tf 沒有 assertion（空測試）"; \
				WARNINGS=$$((WARNINGS + 1)); EMPTY_TESTS=$$((EMPTY_TESTS + 1)); \
			fi; \
		done; \
	done; \
	if [ $$EMPTY_TESTS -eq 0 ]; then echo "  ✅ 無空測試"; fi; \
	echo ""; \
	\
	echo "── 9. SPEC 場景覆蓋（v3.2）──"; \
	NO_MATRIX=0; \
	for spec in docs/specs/SPEC-*.md; do \
		[ -f "$$spec" ] || continue; \
		HM=$$(grep -c "測試矩陣\|Test Matrix" "$$spec" 2>/dev/null || echo 0); \
		if [ "$$HM" = "0" ]; then \
			echo "  🟡 WARNING: $$(basename $$spec) 缺少測試矩陣"; \
			WARNINGS=$$((WARNINGS + 1)); NO_MATRIX=$$((NO_MATRIX + 1)); \
		fi; \
	done; \
	if [ $$NO_MATRIX -eq 0 ] && [ $$SPEC_COUNT -gt 0 ]; then echo "  ✅ 所有 SPEC 有測試矩陣"; \
	elif [ $$SPEC_COUNT -eq 0 ]; then echo "  ⚪ 無 SPEC"; fi; \
	echo ""; \
	\
	echo "=================================" ; \
	echo "🏥 審計摘要：🔴 $$BLOCKERS blocker | 🟡 $$WARNINGS warning | 🟢 $$INFOS info"; \
	if [ $$BLOCKERS -gt 0 ]; then \
		echo "⚠️  有 blocker 需先修復才能開始主任務"; \
	fi; \
	echo ""
	@echo "📊 更新審計基線..."
	@printf '{"last_audit":"%s","test_coverage_ratio":%s,"spec_count":%s,"adr_count":%s,"blockers":%s,"warnings":%s,"info":%s,"lint_warning_count":0,"todo_fixme_count":%s,"side_effects_unverified":0,"rollback_untested_count":0}\n' \
		"$$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$${RATIO:-0}" "$${SPEC_COUNT:-0}" "$${ADR_COUNT:-0}" "$${BLOCKERS:-0}" "$${WARNINGS:-0}" "$${INFOS:-0}" "$${TODO_NO_OWNER:-0}" > .asp-audit-baseline.json 2>/dev/null
	@grep -q "asp-audit-baseline.json" .gitignore 2>/dev/null || echo ".asp-audit-baseline.json" >> .gitignore
	@echo "  ✅ .asp-audit-baseline.json 已更新"

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
	SRC_COUNT=$$(find . -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.java" | grep -v node_modules | grep -v .git | grep -v vendor | wc -l); \
	TEST_COUNT=$$(find . \( -name "*_test.*" -o -name "*.test.*" -o -name "*.spec.*" -o -name "test_*" \) | grep -v node_modules | grep -v .git | wc -l); \
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
	@echo "── scenario-pending ──"
	@grep -rn "scenario-pending" . --include="*.md" 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .asp/profiles || echo "  (無)"
	@echo "── test-pending ──"
	@grep -rn "test-pending" . --include="*.md" 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .asp/profiles || echo "  (無)"

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

#---------------------------------------------------------------------------
# Profile 驗證
#---------------------------------------------------------------------------

profile-validate:
	@bash .asp/scripts/validate-profile.sh
