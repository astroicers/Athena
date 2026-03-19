# AI-SOP-Protocol — Makefile
# 目的：專案層級設定 + 載入 ASP targets
# 使用方式：在 include 之前加入專案自訂 targets

APP_NAME ?= athena
VERSION  ?= latest

# --- 專案自訂 targets 請寫在此區塊 ---

# --- Design Token Validation ---
token-validate:  ## Verify tokens.yaml matches globals.css
	@echo "🎨 Validating design tokens..."
	@python3 -c "\
	import yaml, re; \
	tokens = yaml.safe_load(open('design-system/tokens.yaml')); \
	css = open('frontend/src/styles/globals.css').read(); \
	errors = 0; \
	for section in ['background', 'accent', 'text', 'border', 'status']: \
	    if section not in tokens.get('colors', {}): continue; \
	    for name, t in tokens['colors'][section].items(): \
	        css_var = t.get('css', ''); \
	        val = t.get('value', ''); \
	        if css_var and val and val.startswith('#'): \
	            pattern = css_var.replace('--', r'--') + r':\s*' + re.escape(val); \
	            if not re.search(pattern, css, re.IGNORECASE): \
	                print(f'  MISMATCH: {css_var} expected {val}'); errors += 1; \
	if errors == 0: print('  All tokens in sync ✓'); \
	else: print(f'  {errors} mismatches found'); exit(1)"

token-drift:  ## Scan .tsx files for hardcoded hex colors
	@echo "🔍 Scanning for hardcoded hex in .tsx files..."
	@grep -rn '#[0-9a-fA-F]\{6\}' frontend/src/ --include='*.tsx' \
		| grep -v 'node_modules' \
		| grep -v '// token:' \
		| grep -v 'color-mix' \
		| wc -l | xargs -I{} echo "  {} hardcoded hex values found"
	@grep -rn '#[0-9a-fA-F]\{6\}' frontend/src/ --include='*.tsx' \
		| grep -v 'node_modules' \
		| grep -v '// token:' \
		| grep -v 'color-mix' \
		| head -20

# ASP targets（勿刪除此行）
-include .asp/Makefile.inc
