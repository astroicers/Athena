.PHONY: help build test fmt clippy clean \
        autopilot-init autopilot-validate autopilot-status autopilot-reset \
        session-checkpoint agent-done spec-new \
        k3s-up k3s-down k3s-status \
        db-migrate db-reset

# ── Rust ──────────────────────────────────────────────────────────────────────
build:
	cargo build --workspace

build-release:
	cargo build --workspace --release

test:
	cargo test --workspace

test-filter:
	cargo test --workspace -- $(FILTER)

fmt:
	cargo fmt --all

clippy:
	cargo clippy --workspace -- -D warnings

clean:
	cargo clean

# ── ASP Autopilot ─────────────────────────────────────────────────────────────
autopilot-init:
	@echo "ROADMAP.yaml already exists — edit it directly."

autopilot-validate:
	@echo "=== ROADMAP Validation ==="
	@python3 -c "import yaml,sys; d=yaml.safe_load(open('ROADMAP.yaml')); \
	  total=sum(len(p['tasks']) for p in d['phases']); \
	  done=sum(1 for p in d['phases'] for t in p['tasks'] if t['status']=='completed'); \
	  blocked=sum(1 for p in d['phases'] for t in p['tasks'] if t.get('status')=='blocked'); \
	  print(f'Total tasks: {total}'); print(f'Completed:   {done}'); \
	  print(f'Blocked:     {blocked}'); print(f'Pending:     {total-done-blocked}')" 2>/dev/null \
	  || echo "python3 yaml module required for validation"

autopilot-status:
	@echo "=== Autopilot Status ==="
	@python3 -c "
import yaml, json, os
d = yaml.safe_load(open('ROADMAP.yaml'))
state_file = '.asp-autopilot-state.json'
state = json.load(open(state_file)) if os.path.exists(state_file) else {}
current = state.get('current_task', 'none')
print(f'Current task: {current}')
print()
for phase in d['phases']:
    done = [t for t in phase['tasks'] if t['status'] == 'completed']
    pending = [t for t in phase['tasks'] if t['status'] == 'pending']
    blocked = [t for t in phase['tasks'] if t.get('status') == 'blocked']
    print(f'[{phase[\"id\"]}] {phase[\"name\"]}')
    for t in done:    print(f'  ✅ {t[\"id\"]}: {t[\"title\"]}')
    for t in pending: print(f'  ⬜ {t[\"id\"]}: {t[\"title\"]}')
    for t in blocked: print(f'  🔴 {t[\"id\"]}: {t[\"title\"]} (blocked)')
    print()
" 2>/dev/null || cat ROADMAP.yaml

autopilot-reset:
	@rm -f .asp-autopilot-state.json
	@echo "Autopilot state cleared."

session-checkpoint:
	@python3 -c "
import json, datetime
state = {'status': 'in_progress', 'checkpoint_at': '$(shell date -u +%Y-%m-%dT%H:%M:%SZ)', 'next': '$(NEXT)'}
with open('.asp-autopilot-state.json', 'w') as f: json.dump(state, f, indent=2)
print('Checkpoint saved. Next: $(NEXT)')
" 2>/dev/null

agent-done:
	@python3 -c "
import yaml, json
d = yaml.safe_load(open('ROADMAP.yaml'))
task_id = '$(TASK)'
status = '$(STATUS)'
updated = False
for phase in d['phases']:
    for t in phase['tasks']:
        if t['id'] == task_id:
            t['status'] = 'completed' if status == 'success' else status
            updated = True
if updated:
    with open('ROADMAP.yaml', 'w') as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f'Task {task_id} marked {status}')
else:
    print(f'Task {task_id} not found in ROADMAP.yaml')
" 2>/dev/null

spec-new:
	@mkdir -p docs/specs
	@SLUG=$$(echo "$(TITLE)" | tr ' ' '-' | tr '[:upper:]' '[:lower:]'); \
	  FILE="docs/specs/SPEC-$${SLUG}.md"; \
	  echo "# SPEC: $(TITLE)" > "$$FILE"; \
	  echo "" >> "$$FILE"; \
	  echo "## Goal" >> "$$FILE"; \
	  echo "" >> "$$FILE"; \
	  echo "## Done When" >> "$$FILE"; \
	  echo "" >> "$$FILE"; \
	  echo "## Rollback Plan" >> "$$FILE"; \
	  echo "Created: $$FILE"

# ── k3s ───────────────────────────────────────────────────────────────────────
k3s-up:
	k3s server &
	@echo "k3s starting..."

k3s-down:
	k3s-killall.sh 2>/dev/null || true

k3s-status:
	kubectl get pods --all-namespaces 2>/dev/null || echo "k3s not running"

# ── Database ──────────────────────────────────────────────────────────────────
db-migrate:
	cd crates/athena-db && cargo sqlx migrate run

db-reset:
	cd crates/athena-db && cargo sqlx database drop -y && cargo sqlx database create && cargo sqlx migrate run

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "Athena 2.0 — make targets"
	@echo ""
	@echo "  build              cargo build --workspace"
	@echo "  test               cargo test --workspace"
	@echo "  test-filter        cargo test -- FILTER=<keyword>"
	@echo "  fmt                cargo fmt --all"
	@echo "  clippy             cargo clippy (warnings as errors)"
	@echo ""
	@echo "  autopilot-status   show ROADMAP progress"
	@echo "  autopilot-reset    clear autopilot state"
	@echo "  agent-done         TASK=<id> STATUS=success|failed"
	@echo "  spec-new           TITLE='<title>' — scaffold a SPEC"
	@echo ""
	@echo "  k3s-status         show k3s pod status"
	@echo "  db-migrate         run sqlx migrations"
