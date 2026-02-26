# SPEC-014：Frontend Test Suite

> 為 Athena 前端建立 Vitest + @testing-library/react 測試套件，覆蓋 API 工具函式、元件渲染、Hooks。

| 欄位 | 內容 |
|------|------|
| **規格 ID** | SPEC-014 |
| **關聯 ADR** | ADR-009（前端元件架構） |
| **估算複雜度** | 中 |
| **建議模型** | Sonnet |
| **HITL 等級** | minimal |

---

## 🎯 目標（Goal）

> 建立 Vitest 測試套件，覆蓋 API 工具函式（7 tests）+ 原子元件渲染（12 tests）+ Cards/Data 元件（8 tests）+ Modal/OODA/MITRE/C5ISR 元件（8 tests）+ Hooks（5 tests），共 ~40 tests，使前端 CI 具實質品質保證。

---

## 📥 輸入規格（Inputs）

| 參數名稱 | 型別 | 來源 | 限制條件 |
|----------|------|------|----------|
| 28 個 React 元件 | TSX | `components/` 10 個目錄 | jsdom 環境渲染 |
| 4 個 Hooks | TS | `hooks/*.ts` | renderHook 測試 |
| API 工具函式 | TS | `lib/api.ts` | 純函式 + mock fetch |
| Design System types | TS | `types/*.ts` | Props 型別定義 |

---

## 📤 輸出規格（Expected Output）

**成功情境：**

### 1. Test Infrastructure

- `frontend/vitest.config.ts` — Vitest 配置（jsdom、globals、setup file、vite-tsconfig-paths）
- `frontend/src/test/setup.ts` — @testing-library/jest-dom 全域設定
- `frontend/package.json` — 7 個 test devDependencies + 3 個 scripts

### 2. API Utility Tests（`frontend/src/lib/__tests__/api.test.ts`）

覆蓋：toSnakeCase, toCamelCase, convertKeys (nested/array), toApiBody, fromApiResponse, api.get — 7 tests

### 3. Atom Component Tests（`frontend/src/components/atoms/__tests__/*.test.tsx`）

覆蓋：Button (3), Toggle (3), Badge (2), StatusDot (1), ProgressBar (2), HexIcon (1) — 12 tests

### 4. Card + Data Tests（`frontend/src/components/cards/__tests__/*.test.tsx` + `data/__tests__/*.test.tsx`）

覆蓋：MetricCard (2), TechniqueCard (1), RecommendCard (1), DataTable (3), LogEntryRow (1) — 8 tests

### 5. Modal + OODA + MITRE + C5ISR + Nav Tests

覆蓋：HexConfirmModal (3), OODAIndicator (1), OODATimeline (1), MITRECell (1), DomainCard (1), TabBar (1) — 8 tests

### 6. Hook Tests（`frontend/src/hooks/__tests__/*.test.ts`）

覆蓋：useOperation (2), useOODA (2), useLiveLog (1) — 5 tests

**失敗情境：**

| 錯誤類型 | 處理方式 |
|----------|----------|
| Three.js/WebGL 元件 | 排除 NetworkTopology — jsdom 不支援 WebGL |
| Next.js router hooks | 排除 Sidebar — usePathname 需複雜 mock |
| WebSocket 依賴 | mock WebSocket API 或跳過 useWebSocket |

---

## ⚠️ 邊界條件（Edge Cases）

- Case 1: Three.js/react-force-graph-3d 無法在 jsdom 測試 → 排除 NetworkTopology.tsx
- Case 2: Next.js `usePathname` 需 mock → 排除 Sidebar.tsx
- Case 3: WebSocket API 在 jsdom 需手動 mock → useWebSocket 最小化測試或跳過
- Case 4: `@/*` path alias 需 vite-tsconfig-paths plugin → vitest.config.ts 設定
- Case 5: CSS Tailwind classes 不在 jsdom 中解析 → 測試以 className 存在為準

---

## ✅ 驗收標準（Done When）

- [ ] `cd frontend && npm test` 全數通過（40+ tests, 0 failures）
- [ ] `cd frontend && npm run test:coverage` 報告 > 50% 覆蓋率
- [ ] `make test-frontend` 通過
- [ ] `make test` 前後端皆通過
- [ ] `make lint` 無 error
- [ ] 已更新 `CHANGELOG.md` + `docs/ROADMAP.md`

---

## 🚫 禁止事項（Out of Scope）

- 不要實作 E2E / 瀏覽器自動化測試（Playwright / Cypress）
- 不要測試 NetworkTopology.tsx（WebGL）
- 不要測試 Sidebar.tsx（usePathname 依賴）
- 不要引入 snapshot 測試（脆弱且維護成本高）
- 不要修改既有 production code 來適應測試

---

## 📎 參考資料（References）

- SPEC-005：前端基礎（被測對象）
- SPEC-006：4 畫面實作（被測對象）
- SPEC-013：Backend Test Suite（格式參考）
- ADR-009：前端元件架構（元件分層設計）
