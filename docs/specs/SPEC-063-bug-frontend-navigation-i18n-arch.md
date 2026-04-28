# SPEC-063：BUG-frontend-navigation-i18n-arch

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-063 |
| **關聯 ADR** | 無 |
| **估算複雜度** | 高 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |
| **狀態** | ✅ 完成 |
| **完成日期** | 2026-04-28 |

---

## 🎯 目標

修復 Athena 前端三個層疊問題，導致 sidebar 所有按鈕長期無法點擊：

1. **React hydration error #418**：`NotificationCenter.tsx` 的 `new Date()` 直接寫在 JSX render，SSR/CSR 時間戳不一致，React 放棄 hydration，所有 Link 事件監聽器未附加。
2. **Next.js soft navigation 靜默失敗**：`next-intl` 的 `getRequestConfig` 使用動態 `import()` 讀取 JSON，在 App Router soft navigation 觸發 RSC re-render 時路徑解析失敗，整個 navigation transition 靜默 abort。
3. **`useRouter()` 污染 router context**：在 next-intl `NextIntlClientProvider` 內部呼叫 `useRouter()`，會導致同一頁面的 `<Link>` click handler 執行 `preventDefault()` 放棄導航。

---

## 根本原因分析

| 問題 | 根本原因 | 影響 |
|------|---------|------|
| sidebar 完全無效 | `NotificationCenter.tsx:180` 的 `new Date()` 在 render | React hydration abort → 所有事件監聽器未附加 |
| soft navigation 靜默失敗 | `i18n/request.ts` 動態 `import()` 在 RSC streaming 時路徑解析失敗 | `router.push()` 呼叫後 URL 不變、頁面不動 |
| 部分頁面 Link 失效 | `useRouter()` 與 next-intl router context 衝突 | Link handler 呼叫 `preventDefault()`，不導航 |

---

## 📤 修復方案

### 1. NotificationCenter hydration fix
- 將 `new Date().toLocaleTimeString()` 改為 `useState(() => new Date().toLocaleTimeString())`
- 移除重複的 `if (!isOpen) return null`

### 2. i18n 靜態 import
- `getRequestConfig` 改用靜態 import，打包進 server bundle，消除 RSC runtime 路徑解析問題

### 3. 禁用 `useRouter()`
- 整個專案移除 `useRouter()` 呼叫
- Programmatic navigation 改用 `window.location.href` / `window.location.replace`
- `NavItem` 改用純 `<a href>`（不走 Next.js router）

### 4. 新增 middleware
- 保證首次訪問時 `NEXT_LOCALE` cookie 初始化

### 5. 版本對齊
- `package.json` next 版本從 `^14.1.0` 升至 `^14.2.35`，與 `eslint-config-next` 對齊

---

## 🔗 追溯性

| 實作檔案 | 說明 | 最後驗證日期 |
|----------|------|-------------|
| `frontend/src/components/layout/NotificationCenter.tsx` | useState 穩定化 mountTime，移除重複 early return | 2026-04-28 |
| `frontend/src/i18n/request.ts` | 動態 import 改靜態 import | 2026-04-28 |
| `frontend/src/components/nav/NavItem.tsx` | Link → 純 `<a href>` | 2026-04-28 |
| `frontend/src/app/operations/page.tsx` | 移除 useRouter，改 window.location.href | 2026-04-28 |
| `frontend/src/app/poc/page.tsx` | 移除 useRouter，改 window.location.replace | 2026-04-28 |
| `frontend/src/app/opsec/page.tsx` | 移除 useRouter，改 window.location.replace | 2026-04-28 |
| `frontend/src/components/cards/TechniqueCard.tsx` | 移除 useRouter，改 window.location.href | 2026-04-28 |
| `frontend/src/middleware.ts` | 新增，保證 NEXT_LOCALE cookie 初始化 | 2026-04-28 |
| `frontend/package.json` | next 版本升至 ^14.2.35 | 2026-04-28 |
| `frontend/next.config.js` | 移除 output: standalone（與 Dockerfile 衝突） | 2026-04-28 |
| `frontend/Dockerfile` | 改用 next start 模式 | 2026-04-28 |

---

## ✅ 驗收標準

- [x] sidebar 所有按鈕可點擊，頁面正確跳轉
- [x] Console 無 React hydration error #418
- [x] 語言切換（LocaleSwitcher）正常運作
- [x] 從任意頁面點擊 sidebar 均可導航
- [x] `next start` 啟動無警告

---

## ⚠️ 已知限制與後續

- **soft navigation 已放棄**：`window.location.href` 是全頁重整，無 SPA 的無閃爍跳轉體驗。根本解法是升級 next-intl 至與 Next.js 14.2.x 完全相容的版本，或遷移至 URL-prefix locale 模式。
- **`tech-debt: test-pending`**：navigation 行為的自動化測試待補。
- **後續改進**：評估 next-intl URL-prefix 模式（`/en/warroom`）以支援 SEO 與深度連結。
