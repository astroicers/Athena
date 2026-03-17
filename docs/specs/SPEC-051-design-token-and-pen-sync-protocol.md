# SPEC-051：Design Token 與 .pen 設計同步協議

> 定義 UI 設計 token 的唯一真相來源、同步流程、以及常見錯誤的防護規則。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-051 |
| **關聯 ADR** | ADR-009（Frontend Component Architecture） |
| **估算複雜度** | 低 |
| **建議模型** | Sonnet |
| **HITL 等級** | standard |

---

## 🎯 目標（Goal）

> **確保 .pen 設計檔案永遠是 UI 的唯一真相來源，前端代碼必須忠實反映 .pen 設計，並防止設計 token 漂移。**

---

## 📐 Design Token 定義（Single Source of Truth）

### 色彩 Token

| Token 名稱 | Hex 值 | 用途 |
|-----------|--------|------|
| `--bg-base` | `#0a0e17` | 頁面背景 |
| `--bg-surface` | `#111827` | 卡片、面板背景 |
| `--border-default` | `#1f2937` | 一般卡片邊框（有內容時） |
| `--border-subtle` | `white/5`（≈ `#FFFFFF0D`） | 空狀態、低調邊框 |
| `--border-input` | `#1f2937` | 輸入框邊框 |
| `--text-primary` | `#e5e7eb` | 主要文字 |
| `--text-secondary` | `#9ca3af` | 次要文字、label |
| `--text-tertiary` | `#6b7280` | 提示文字、hint |
| `--accent` | `#3b82f6` | 主強調色 |
| `--success` | `#22C55E` | 成功、通過 |
| `--warning` | `#FBBF24` | 警告 |
| `--error` | `#EF4444` | 錯誤、危險 |
| `--orange` | `#F97316` | 次要警告 |
| `--cyan` | `#06B6D4` | 資訊強調 |
| `--purple` | `#A855F7` | 類別標記 |

### 字體 Token

| Token | Value |
|-------|-------|
| `--font-mono` | `IBM Plex Mono` |
| `--corner-card` | `6px`（小卡片）/ `8px`（大面板） |
| `--corner-badge` | `4px` |

---

## 🚫 禁止的模式（Anti-Patterns）

以下模式已造成過 bug，**禁止使用**：

### 1. 重複 border class（缺色）
```tsx
// ❌ 錯誤：border 重複、缺少顏色 → 瀏覽器默認灰色邊框
className="border border rounded p-3"

// ✅ 正確：
className="border border-[#1f2937] rounded-lg p-3"
```

### 2. 邊框 alpha 不一致
```tsx
// ❌ 錯誤：混用 alpha 後綴
className="border-[#1f293740]"  // 有的 40，有的沒有

// ✅ 正確：統一使用不透明或 Tailwind opacity 語法
className="border-[#1f2937]"       // 有內容的卡片
className="border-white/5"         // 空狀態、低調邊框
```

### 3. 混用 `#374151` 與 `#1f2937`
```tsx
// ❌ 錯誤：Tailwind gray-700 與設計 token 混用
className="border-[#374151]"

// ✅ 正確：統一使用設計 token
className="border-[#1f2937]"
```

### 4. TabBar alignItems 錯誤
```tsx
// ❌ 錯誤：items-end 讓 tab 文字沈到底部
className="flex items-end h-10"

// ✅ 正確：items-center + button h-full
className="flex items-center h-10"
// button: className="h-full flex items-center"
// active indicator: absolute bottom-0
```

### 5. 空狀態缺少背景色
```tsx
// ❌ 錯誤：只有邊框沒有背景，在深色頁面上突兀
className="border border-[#1f2937] rounded p-3"

// ✅ 正確：邊框 + 背景統一
className="bg-[#111827] border border-white/5 rounded-lg p-6"
```

### 6. 部署後沒生效
```bash
# ❌ 錯誤：直接 npx next start（Docker 環境下無效）
npx next start -p 58080

# ✅ 正確：重建 Docker image
docker compose build frontend && docker compose up -d frontend
```

---

## 📐 元件樣式速查表

### 空狀態（Empty State）
```tsx
<div className="bg-[#111827] border border-white/5 rounded-lg p-6 text-center">
  <span className="text-xs font-mono text-[#9ca3af]">{message}</span>
</div>
```

### 有內容的卡片（Content Card）
```tsx
<div className="bg-[#111827] border border-[#1f2937] rounded-lg p-4">
  {children}
</div>
```

### 輸入框（Input Field）
```tsx
<input className="w-full bg-[#0A0E17] border border-[#1f2937] rounded px-3 py-2 text-sm font-mono text-[#e5e7eb] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6]" />
```

### TabBar
```tsx
<div className="flex items-center h-10 px-4 bg-[#0f1729] border-b border-[#1f2937]">
  <button className="relative h-full px-4 text-xs font-mono flex items-center">
    {label}
    {isActive && <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-[#3b82f6]" />}
  </button>
</div>
```

### Section Header
```tsx
<h2 className="text-xs font-mono font-bold text-[#e5e7eb] uppercase tracking-wider">
  {title}
</h2>
```

---

## 🔄 .pen ↔ Code 同步流程

### 新增/修改 UI 組件時

1. **先更新 .pen 設計**（pencil-new-v2.pen）
2. 使用 `batch_get` 確認 .pen 節點存在
3. 使用 `get_screenshot` 視覺驗證
4. **再寫前端代碼**，嚴格遵循 .pen 的 token
5. `docker compose build frontend && docker compose up -d frontend`
6. 瀏覽器 hard refresh 驗證

### 修復 bug 時

1. 對比 .pen 設計與瀏覽器實際畫面
2. 找出 code 中與 .pen 不一致的 token
3. 修復代碼
4. 同步修復 .pen（如果 .pen 本身也有問題）
5. 重建 Docker 部署

---

## ✅ 驗收標準（Done When）

- [ ] 所有前端組件的 border/bg/text 色彩來自上方 token 表
- [ ] 無任何 `border border ` 重複 class
- [ ] 無任何 `#374151` 邊框色（統一用 `#1f2937`）
- [ ] 所有空狀態使用 `bg-[#111827] border-white/5 rounded-lg p-6`
- [ ] 所有 TabBar 使用 `items-center` + `h-full`
- [ ] .pen 設計中所有 TabBar `alignItems` 為 `"center"`
- [ ] 部署使用 `docker compose build frontend`

---

## 🚫 禁止事項（Out of Scope）

- 不重新定義 Tailwind theme（保持 hardcoded hex 直到 CSS variable 遷移完成）
- 不改變 .pen 檔案結構或 frame layout

---

## 📎 參考資料（References）

- ADR-009：Frontend Component Architecture
- `frontend/DESIGN_MAP.md`：.pen Frame ↔ Code 對應
- `design/pencil-new-v2.pen`：設計唯一真相來源
- `frontend/src/styles/globals.css`：CSS 變數定義
- `frontend/tailwind.config.ts`：Tailwind 擴展配置
