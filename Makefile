# AI-SOP-Protocol — Makefile
# 目的：專案層級設定 + 載入 ASP targets
# 使用方式：在 include 之前加入專案自訂 targets

APP_NAME ?= athena
VERSION  ?= latest

# --- 專案自訂 targets 請寫在此區塊 ---

.PHONY: relay-script

relay-script: ## SPEC-054: Generate SSH reverse tunnel script for relay machine
	@echo "🛰️  Generating SPEC-054 relay port-forwarding script..."
	@mkdir -p tmp
	@docker exec athena-backend-1 python3 -m app.cli.generate_relay_script \
		> tmp/athena-relay.sh
	@chmod +x tmp/athena-relay.sh
	@echo "✅ Script: tmp/athena-relay.sh"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Ensure your SSH key is on the relay (~/.ssh/authorized_keys)"
	@echo "  2. scp tmp/athena-relay.sh <user>@<relay_ip>:~/"
	@echo "  3. ssh <user>@<relay_ip> ./athena-relay.sh"
	@echo "  4. Leave it running. Ctrl+C stops + cleans up (no residue)."

# ASP targets（勿刪除此行）
-include .asp/Makefile.inc
