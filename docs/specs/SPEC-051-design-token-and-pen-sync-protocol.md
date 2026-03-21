# SPEC-051：Design Token 與 .pen 設計同步協議

> 定義 UI 設計 token 的唯一真相來源、同步流程、驗證工具、以及 Tailwind v4 相容性規則。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-051 |
| **關聯 ADR** | ADR-009（Frontend Component Architecture）、ADR-041（Adopt Deep Gemstone v3 Design System） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 目標（Goal）

> **確保 .pen 設計檔案永遠是 UI 的唯一真相來源，前端代碼必須忠實反映 .pen 設計，並透過自動化工具防止設計 token 漂移。**

---

## Token 信任鏈（Trust Chain）

Token 的定義與傳播遵循嚴格的單向信任鏈。**上游變更時，所有下游必須同步更新。**

```
pencil-new-v2.pen（唯一真相來源 — 設計師定義色彩/字型/間距）
  │
  ▼
design-system/tokens.yaml（結構化定義 — 機器可讀格式）
  │
  ▼
frontend/src/styles/globals.css（CSS 變數宣告 — 瀏覽器運行時使用）
  │
  ▼
frontend/tailwind.config.ts（Tailwind 擴展 — utility class 映射）
  │
  ▼
frontend/src/lib/designTokens.ts（JS 常數 — 程式邏輯中使用）
  │
  ▼
前端組件代碼（消費端 — 只引用 CSS vars 或 Tailwind classes）
```

### 各層級職責

| 層級 | 檔案路徑 | 格式 | 職責 |
|------|----------|------|------|
| 設計稿 | `design/pencil-new-v2.pen` | .pen (encrypted) | 色彩、字型、間距的視覺定義。所有設計決策的原點 |
| Token 定義 | `design-system/tokens.yaml` | YAML | 將 pen 設計稿中的值結構化為 `colors.accent.value: "#1E6091"` 格式 |
| CSS 實作 | `frontend/src/styles/globals.css` | CSS | 將 tokens.yaml 值宣告為 CSS custom properties（`--color-accent: #1E6091`） |
| Tailwind 映射 | `frontend/tailwind.config.ts` | TypeScript | 將 CSS vars 映射為 Tailwind utility classes |
| JS 常數 | `frontend/src/lib/designTokens.ts` | TypeScript | 匯出 token 值供程式邏輯使用（條件判斷、動態樣式等） |

---

## Deep Gemstone v3 色票參考

> 完整定義見 `design-system/tokens.yaml`，此處列出核心色票供快速查閱。

### 背景色（Background）

| 名稱 | Hex 值 | CSS 變數 | 用途 |
|------|--------|----------|------|
| Base | `#09090B` | `--color-bg-base` | 頁面最底層背景 |
| Card | `#18181B` | `--color-bg-card` | 卡片、面板背景 |
| Hover | `#27272A` | `--color-bg-hover` | 懸停態、輸入框背景 |

### 強調色（Accent / Status）

| 名稱 | Hex 值 | CSS 變數 | 用途 |
|------|--------|----------|------|
| Sapphire Blue | `#1E6091` | `--color-accent` | 主強調色、連結、活躍狀態 |
| Emerald | `#059669` | `--color-success` | 成功、完成狀態 |
| Amber | `#B45309` | `--color-warning` | 警告、注意事項 |
| Deep Red | `#B91C1C` | `--color-error` | 錯誤、危險狀態 |

### 字型（Typography）

| 字型 | 用途 | CSS 變數 |
|------|------|----------|
| JetBrains Mono | 主要字型、代碼、數據 | `--font-primary` |
| Inter | 輔助字型、正文 | `--font-secondary` |

### 圓角（Border Radius）

統一使用 4px（Tailwind `rounded`）。禁止混用 `rounded-lg` / `rounded-xl`，除非 pen 設計稿明確指定。

---

## CRITICAL: Tailwind v4 Border Workaround

Tailwind v4 改變了 `border-color` 的計算方式。自訂的 `border-athena-*` utility class 在 Tailwind v4 下**無法正確套用顏色**，邊框會退化為瀏覽器預設灰色。

### 禁止的模式

```tsx
// PROHIBITED: border-athena-* 在 Tailwind v4 下不生效
className="border border-athena-accent"
className="border-athena-surface"
className="border-athena-dim"
```

### 正確的模式

```tsx
// CORRECT: 使用 CSS 變數直接引用
className="border border-[var(--color-accent)]"
className="border border-[var(--color-border)]"

// CORRECT: 使用 Tailwind 內建色彩（不受影響）
className="border border-white/5"
className="border border-zinc-700"
```

### 偵測規則

```bash
# 掃描所有 .tsx 檔案中的 border-athena-* 使用
grep -rn "border-athena" frontend/src/ --include='*.tsx'
# 預期結果：零匹配
```

---

## 禁止的模式（Anti-Patterns）

以下模式已造成過 bug，**禁止使用**：

### 1. 重複 border class（缺色）
```tsx
// WRONG: border 重複、缺少顏色 -> 瀏覽器默認灰色邊框
className="border border rounded p-3"

// CORRECT:
className="border border-[var(--color-border)] rounded p-3"
```

### 2. 邊框 alpha 不一致
```tsx
// WRONG: 混用 alpha 後綴
className="border-[#1f293740]"  // 有的 40，有的沒有

// CORRECT: 統一使用 CSS 變數或 Tailwind opacity 語法
className="border-[var(--color-border)]"   // 有內容的卡片
className="border-white/5"                  // 空狀態、低調邊框
```

### 3. Hardcoded hex 替代 CSS 變數
```tsx
// WRONG: 直接寫 hex 值
className="bg-[#18181B] border-[#27272A] text-[#e5e7eb]"

// CORRECT: 使用 CSS 變數
className="bg-[var(--color-bg-card)] border-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
```

### 4. TabBar alignItems 錯誤
```tsx
// WRONG: items-end 讓 tab 文字沈到底部
className="flex items-end h-10"

// CORRECT: items-center + button h-full
className="flex items-center h-10"
// button: className="h-full flex items-center"
// active indicator: absolute bottom-0
```

### 5. 空狀態缺少背景色
```tsx
// WRONG: 只有邊框沒有背景，在深色頁面上突兀
className="border border-[var(--color-border)] rounded p-3"

// CORRECT: 邊框 + 背景統一
className="bg-[var(--color-bg-card)] border border-white/5 rounded p-6"
```

### 6. 部署後沒生效
```bash
# WRONG: 直接 npx next start（Docker 環境下無效）
npx next start -p 58080

# CORRECT: 重建 Docker image
docker compose build frontend && docker compose up -d frontend
```

---

## 元件樣式速查表

### 空狀態（Empty State）
```tsx
<div className="bg-[var(--color-bg-card)] border border-white/5 rounded p-6 text-center">
  <span className="text-xs font-mono text-[var(--color-text-muted)]">{message}</span>
</div>
```

### 有內容的卡片（Content Card）
```tsx
<div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded p-4">
  {children}
</div>
```

### 輸入框（Input Field）
```tsx
<input className="w-full bg-[var(--color-bg-base)] border border-[var(--color-border)] rounded px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]" />
```

### TabBar
```tsx
<div className="flex items-center h-10 px-4 bg-[var(--color-bg-base)] border-b border-[var(--color-border)]">
  <button className="relative h-full px-4 text-xs font-mono flex items-center">
    {label}
    {isActive && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-[var(--color-accent)]" />}
  </button>
</div>
```

### Section Header
```tsx
<h2 className="text-xs font-mono font-bold text-[var(--color-text-primary)] uppercase tracking-wider">
  {title}
</h2>
```

---

## 驗證工具

### `make token-validate`

驗證 `tokens.yaml` 中定義的每個 token 都有對應的 CSS 變數宣告在 `globals.css` 中，且 hex 值匹配。

```bash
make token-validate
# 成功輸出: "All tokens in sync"
# 失敗輸出: "MISMATCH: --color-accent expected #1E6091"
```

**驗證邏輯：**
1. 解析 `design-system/tokens.yaml` 中所有 `colors.*` 條目
2. 對每個條目，在 `globals.css` 中搜尋 `{css_var}: {hex_value}`
3. 不匹配則報錯

### `make token-drift`

掃描所有 `.tsx` 檔案，偵測 hardcoded hex 值（應該使用 CSS 變數的地方）。

```bash
make token-drift
# 輸出: 列出所有包含 hardcoded hex 的行
# 目標: 零新增（允許已知例外）
```

---

## .pen <-> Code 同步流程

### 新增/修改 UI 組件時

1. **先更新 .pen 設計**（pencil-new-v2.pen）
2. 使用 `batch_get` 確認 .pen 節點存在
3. 使用 `get_screenshot` 視覺驗證
4. 若引入新色彩/token：更新 tokens.yaml -> globals.css -> tailwind.config.ts -> designTokens.ts
5. **再寫前端代碼**，嚴格使用 CSS 變數引用
6. `docker compose build frontend && docker compose up -d frontend`
7. 瀏覽器 hard refresh 驗證
8. 執行 `make token-validate` 和 `make token-drift` 確認無漂移

### 修復 bug 時

1. 對比 .pen 設計與瀏覽器實際畫面
2. 找出 code 中與 .pen 不一致的 token
3. 修復代碼（使用 CSS 變數，不用 hardcoded hex）
4. 同步修復 .pen（如果 .pen 本身也有問題）
5. 重建 Docker 部署
6. 執行 `make token-validate`

### 修改色彩定義時

1. 在 pencil-new-v2.pen 中更新色彩
2. 同步更新 `design-system/tokens.yaml`
3. 同步更新 `frontend/src/styles/globals.css`
4. 確認 `frontend/tailwind.config.ts` 映射正確
5. 確認 `frontend/src/lib/designTokens.ts` 常數正確
6. 執行 `make token-validate`
7. 執行 `make token-drift`

---

## ASP Profile 整合（Anti-Drift Rules）

`design_dev.md` profile 中定義了以下自動化防護規則：

1. **Auto-validate**：任何觸及 `globals.css`、`tokens.yaml`、`tailwind.config.ts` 的修改，自動觸發 `make token-validate`
2. **Drift warning**：任何新增 `.tsx` 檔案或修改 className 的 PR，自動觸發 `make token-drift`
3. **border-athena ban**：grep 偵測到 `border-athena-*` 使用時，阻止提交

---

## 驗收標準（Done When）

- [ ] 所有前端組件的 border/bg/text 色彩使用 CSS 變數引用（`var(--color-*)`）
- [ ] 無任何 `border border ` 重複 class
- [ ] 無任何 `border-athena-*` class 使用
- [ ] 無任何新增 hardcoded hex 值（`make token-drift` 零新增）
- [ ] `make token-validate` 通過（tokens.yaml 與 globals.css 完全匹配）
- [ ] 所有空狀態使用 `bg-[var(--color-bg-card)] border-white/5 rounded p-6`
- [ ] 所有 TabBar 使用 `items-center` + `h-full`
- [ ] .pen 設計中所有 TabBar `alignItems` 為 `"center"`
- [ ] 部署使用 `docker compose build frontend`
- [ ] 信任鏈五層全部同步（pen -> tokens.yaml -> globals.css -> tailwind.config -> designTokens.ts）

---

## 禁止事項（Out of Scope）

- 不在此 SPEC 範圍內重新定義 Tailwind theme 結構（保持 CSS variable 引用模式）
- 不改變 .pen 檔案結構或 frame layout
- 不引入 build-time token injection（除非 CSS vars 效能被證明有問題）

---

## 參考資料（References）

- ADR-009：Frontend Component Architecture
- ADR-041：Adopt Deep Gemstone v3 Design System
- `frontend/DESIGN_MAP.md`：.pen Frame <-> Code 對應
- `design/pencil-new-v2.pen`：設計唯一真相來源
- `design-system/tokens.yaml`：結構化 token 定義
- `frontend/src/styles/globals.css`：CSS 變數定義
- `frontend/tailwind.config.ts`：Tailwind 擴展配置
- `frontend/src/lib/designTokens.ts`：JS token 常數
