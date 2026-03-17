# UI/UX 規格書 (UI/UX Specification)

> **使用說明**：複製此模板至專案 `docs/UIUX_SPEC.md`。本文件須與 `SRS.md` 第 8 節「介面規格」保持同步。設計稿連結請置於各節頂部。

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | <!-- TODO: 填入專案名稱 --> |
| **版本** | v0.1.0 |
| **最後更新** | <!-- TODO: YYYY-MM-DD --> |
| **狀態** | Draft / Review / Accepted |
| **設計稿連結** | <!-- TODO: Figma / Zeplin 連結 --> |
| **設計師** | <!-- TODO: 填入設計師 --> |
| **前端負責人** | <!-- TODO: 填入前端負責人 --> |

---

## 1. Design System

> **注意：** 若專案使用現成 Design System（如 Material UI、Ant Design、shadcn/ui），本節記錄客製化覆寫規則即可。

### 1.1 Color Palette（色彩系統）

#### 品牌色（Brand Colors）

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-primary-50` | `#EFF6FF` | 淺色背景、Hover 狀態 |
| `--color-primary-100` | `#DBEAFE` | 選取狀態背景 |
| `--color-primary-500` | `#3B82F6` | 主要按鈕、連結、重點元素 |
| `--color-primary-600` | `#2563EB` | 按鈕 Hover 狀態 |
| `--color-primary-700` | `#1D4ED8` | 按鈕 Active 狀態 |
| `--color-primary-900` | `#1E3A8A` | 深色文字 |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO: 自訂品牌色 --> |

#### 語意色（Semantic Colors）

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-success-500` | `#22C55E` | 成功狀態、正向反饋 |
| `--color-warning-500` | `#F59E0B` | 警告、需注意事項 |
| `--color-danger-500` | `#EF4444` | 錯誤、危險操作 |
| `--color-info-500` | `#06B6D4` | 資訊提示 |

#### 中性色（Neutral Colors）

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-gray-50` | `#F9FAFB` | 頁面背景 |
| `--color-gray-100` | `#F3F4F6` | 卡片、輸入框背景 |
| `--color-gray-300` | `#D1D5DB` | 邊框、分隔線 |
| `--color-gray-500` | `#6B7280` | 次要文字、Placeholder |
| `--color-gray-700` | `#374151` | 次要標題 |
| `--color-gray-900` | `#111827` | 主要文字 |
| `--color-white` | `#FFFFFF` | 卡片背景、按鈕文字 |

#### 暗色模式覆寫（Dark Mode）

<!-- TODO: 若支援暗色模式，填寫對應 Token -->

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| `--color-bg-primary` | `#FFFFFF` | `#0F172A` |
| `--color-bg-secondary` | `#F9FAFB` | `#1E293B` |
| `--color-text-primary` | `#111827` | `#F8FAFC` |
| `--color-text-secondary` | `#6B7280` | `#94A3B8` |

---

### 1.2 Typography Scale（字體排版）

**字體族：** <!-- TODO: e.g., Inter（英文）、Noto Sans TC（繁體中文） -->

```css
/* 字體載入 */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
/* 繁體中文字體 */
font-family: 'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif;
```

| Token | Font Size | Line Height | Font Weight | 用途 |
|-------|-----------|-------------|-------------|------|
| `--text-xs` | 12px | 16px | 400 | 標籤、輔助說明 |
| `--text-sm` | 14px | 20px | 400 | 表格內容、次要資訊 |
| `--text-base` | 16px | 24px | 400 | 主要內文 |
| `--text-lg` | 18px | 28px | 500 | 卡片標題、強調文字 |
| `--text-xl` | 20px | 28px | 600 | 區塊標題 |
| `--text-2xl` | 24px | 32px | 700 | 頁面標題 |
| `--text-3xl` | 30px | 36px | 700 | 首頁大標題 |
| `--text-4xl` | 36px | 40px | 700 | Landing Page Hero |

---

### 1.3 Spacing System（間距系統）

基礎單位：**4px**（Tailwind 預設模式）

| Token | Value | 用途範例 |
|-------|-------|----------|
| `spacing-1` | 4px | 元素內小間距、Icon 與文字間距 |
| `spacing-2` | 8px | 元素內側距、標籤間距 |
| `spacing-3` | 12px | 表單欄位間距 |
| `spacing-4` | 16px | 卡片 Padding、Section 間距 |
| `spacing-6` | 24px | 卡片間距、主要 Padding |
| `spacing-8` | 32px | Section 分隔 |
| `spacing-12` | 48px | 大型 Section 間距 |
| `spacing-16` | 64px | 頁面頂部 Hero 間距 |

---

### 1.4 Component Library（元件庫）

**基礎元件庫：** <!-- TODO: e.g., shadcn/ui / Radix UI / Headless UI -->

**客製化元件清單（依開發優先級排序）：**

| 元件 | 優先級 | 對應頁面 | 備註 |
|------|--------|----------|------|
| `Button` | P0 | 全站 | 覆寫品牌色 |
| `Input` / `TextArea` | P0 | 全站 | 含錯誤狀態 |
| `DataTable` | P0 | 管理後台 | 含排序、分頁 |
| `Modal` / `Dialog` | P1 | 全站 | 確認對話框 |
| `Toast` / `Notification` | P1 | 全站 | 操作反饋 |
| `Sidebar` | P1 | Dashboard | 可收合導航 |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | |

---

## 2. 頁面流程

### 2.1 使用者旅程地圖（User Journey Map）

#### 旅程：新使用者首次使用

```
發現 → 訪問 Landing → 點擊「免費試用」→ 填寫註冊表單
  → 收到驗證信 → 點擊驗證連結 → 首次登入
  → 引導教學（Onboarding）→ 完成首個核心任務
```

**各階段情緒曲線（1-10）：**
- 發現：7（期待）
- 訪問 Landing：6（評估中）
- 填寫表單：5（輕微阻力）
- 收驗證信：4（等待中）
- 首次登入：8（成功感）
- 完成首個任務：9（高滿意度）

**痛點與優化機會：**
- 驗證信可能進垃圾信匣 → 提示使用者檢查 + 重發按鈕
- 表單欄位過多 → 分步驟填寫（Progressive Disclosure）

---

#### 旅程：<!-- TODO: 核心業務旅程 -->

```
<!-- TODO: 描述核心業務的使用者旅程 -->
```

### 2.2 導航結構（Information Architecture）

```
首頁 Landing (/)
│
├── 未登入狀態
│   ├── 登入 (/login)
│   ├── 註冊 (/register)
│   └── 忘記密碼 (/forgot-password)
│
└── 已登入狀態
    ├── 儀表板 (/dashboard)            [預設首頁]
    │   └── 總覽概況
    │
    ├── [核心功能模組] (/feature-a)    <!-- TODO: 按業務填寫 -->
    │   ├── 列表頁 (/feature-a)
    │   ├── 新增頁 (/feature-a/new)
    │   └── 詳情頁 (/feature-a/:id)
    │
    ├── 個人設定 (/settings)
    │   ├── 個人資料 (/settings/profile)
    │   ├── 安全設定 (/settings/security)
    │   └── 通知設定 (/settings/notifications)
    │
    └── [Admin Only] 管理後台 (/admin)
        ├── 使用者管理 (/admin/users)
        └── 系統設定 (/admin/settings)
```

---

## 3. 元件規格

> 每個自定義元件需定義：Props、States、Behavior、無障礙需求。

### 3.1 Button 元件

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `variant` | `'primary' \| 'secondary' \| 'outline' \| 'ghost' \| 'danger'` | `'primary'` | 視覺樣式 |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | 尺寸 |
| `disabled` | `boolean` | `false` | 禁用狀態 |
| `loading` | `boolean` | `false` | 載入中（顯示 Spinner） |
| `leftIcon` | `ReactNode` | — | 左側圖示 |
| `rightIcon` | `ReactNode` | — | 右側圖示 |
| `fullWidth` | `boolean` | `false` | 撐滿父容器寬度 |

**States：**

| 狀態 | 視覺效果 |
|------|----------|
| Default | 品牌色背景，白色文字 |
| Hover | 背景加深 10%（`primary-600`） |
| Active / Pressed | 背景加深 20%（`primary-700`） |
| Focus | 2px `primary-500` Outline，offset 2px（Keyboard nav） |
| Disabled | 50% Opacity，cursor `not-allowed` |
| Loading | 顯示旋轉 Spinner，文字保留（防 Layout Shift） |

**Behavior：**
- `loading` 狀態自動套用 `disabled`，防止重複提交
- 非 `<button>` 渲染時（as Link）需保留 role 語意

---

### 3.2 DataTable 元件

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| `columns` | `ColumnDef[]` | 必填 | 欄位定義 |
| `data` | `T[]` | 必填 | 資料陣列 |
| `loading` | `boolean` | `false` | Skeleton 載入狀態 |
| `pagination` | `PaginationConfig` | — | 分頁設定 |
| `onSort` | `(field, direction) => void` | — | 排序回調 |
| `selectable` | `boolean` | `false` | 多選 Checkbox |
| `onSelect` | `(selectedRows) => void` | — | 選取回調 |
| `emptyState` | `ReactNode` | 預設空狀態 | 無資料時顯示 |

**States：**

| 狀態 | 說明 |
|------|------|
| Loading | 每行顯示 Skeleton（高度與實際行同） |
| Empty | 居中顯示圖示 + 說明 + CTA 按鈕 |
| Error | 顯示錯誤訊息 + 重試按鈕 |
| Partial Loading | 保留現有資料，頂部顯示細進度條 |

---

### 3.3 <!-- TODO: 業務核心元件 -->

**Props：**

| Prop | Type | Default | 說明 |
|------|------|---------|------|
| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

**States：**

| 狀態 | 視覺效果 |
|------|----------|
| <!-- TODO --> | <!-- TODO --> |

---

## 4. 響應式規則

### 4.1 Breakpoints

| 名稱 | 寬度範圍 | 目標裝置 |
|------|----------|----------|
| `xs` (mobile) | < 480px | 小型手機 |
| `sm` (mobile-lg) | 480px - 767px | 大型手機 |
| `md` (tablet) | 768px - 1023px | 平板、橫向手機 |
| `lg` (desktop) | 1024px - 1279px | 筆電、小型桌機 |
| `xl` (desktop-lg) | 1280px - 1535px | 標準桌機 |
| `2xl` (wide) | ≥ 1536px | 大型螢幕 |

### 4.2 各尺寸佈局策略

| 頁面/元件 | Mobile (xs-sm) | Tablet (md) | Desktop (lg+) |
|-----------|----------------|-------------|---------------|
| 導航 | 漢堡選單（抽屜式） | 頂部 Navbar + 折疊選單 | 左側固定 Sidebar |
| 儀表板 | 單欄堆疊 | 2 欄 Grid | 3-4 欄 Grid |
| 表單 | 全寬，標籤在上 | 全寬，標籤在上 | 半寬，標籤靠左 |
| DataTable | 卡片式（Card List） | 橫向捲動表格 | 完整表格 |
| Modal | 全螢幕 Sheet | 置中 Dialog（80% 寬） | 置中 Dialog（max 600px） |

### 4.3 觸控友善規則

- 最小點擊目標：**44x44px**（WCAG 2.1 AAA）
- 表單欄位高度：Mobile 至少 **48px**（防 iOS 自動縮放）
- 避免 Hover-only 互動（手機無 Hover）
- 滑動手勢：僅用於明確的 Swipe 場景（如圖片輪播），並提供替代操作

---

## 5. 無障礙標準（Accessibility）

### 5.1 合規目標

- **WCAG 等級：** 2.1 AA（最低要求），關鍵功能追求 AAA
- **測試工具：** axe DevTools、Lighthouse、NVDA（Windows）、VoiceOver（macOS）

### 5.2 色彩對比度

| 組合 | 最小比率要求 | 實際比率 | 通過 |
|------|-------------|----------|------|
| 主要文字（`gray-900` on `white`） | 4.5:1 (AA) | 21:1 | ✓ |
| 次要文字（`gray-500` on `white`） | 4.5:1 (AA) | 7.0:1 | ✓ |
| 按鈕文字（`white` on `primary-500`） | 4.5:1 (AA) | 5.9:1 | ✓ |
| <!-- TODO: 驗證所有顏色組合 --> | | | |

### 5.3 鍵盤導航（Keyboard Navigation）

| 場景 | 行為 |
|------|------|
| Tab 順序 | 與視覺閱讀順序一致，不得跳過互動元素 |
| Focus 樣式 | 2px `primary-500` Outline，offset 2px，不得使用 `outline: none` |
| Modal 開啟 | Focus 移至 Modal 第一個互動元素 |
| Modal 關閉 | Focus 返回觸發按鈕 |
| Dropdown | Arrow 鍵導航選項，Enter 選取，Escape 關閉 |
| DataTable | Tab 進入表格，Arrow 鍵移動儲存格，Space 選取 |
| Form 驗證 | 錯誤訊息與欄位透過 `aria-describedby` 連結 |

### 5.4 Screen Reader 支援

- **語意 HTML 優先：** 使用正確的 `<button>`, `<nav>`, `<main>`, `<section>` 標籤
- **ARIA 使用原則：** 僅於語意 HTML 不足時使用；不重複原生語意
- **圖示按鈕：** 必須有 `aria-label`（如 `<button aria-label="關閉">`）
- **純裝飾圖片：** `alt=""`；有意義圖片：提供完整描述
- **狀態通知：** 動態內容更新使用 `aria-live="polite"`（非緊急）或 `"assertive"`（錯誤）
- **表格：** 必須有 `<caption>` 或 `aria-label`；複雜表格使用 `scope`, `headers`

### 5.5 表單無障礙

```html
<!-- 正確示範 -->
<div>
  <label for="email">電子郵件地址 <span aria-hidden="true">*</span></label>
  <input
    id="email"
    type="email"
    required
    aria-required="true"
    aria-describedby="email-error"
    aria-invalid="true"  <!-- 僅在有錯誤時 -->
  />
  <p id="email-error" role="alert">請輸入有效的電子郵件地址</p>
</div>
```

---

## 6. 動畫與互動

### 6.1 Transition 規則

| 場景 | Duration | Easing | 說明 |
|------|----------|--------|------|
| 按鈕 Hover | 150ms | `ease-out` | 顏色、背景變化 |
| 按鈕 Active | 75ms | `ease-in` | 快速響應 |
| Modal 開啟 | 200ms | `ease-out` | Fade + Scale（0.95 → 1） |
| Modal 關閉 | 150ms | `ease-in` | Fade + Scale（1 → 0.95） |
| Drawer 滑入 | 300ms | `ease-out` | Slide from edge |
| Toast 出現 | 300ms | `spring` | Slide in + Fade |
| Toast 消失 | 200ms | `ease-in` | Slide out + Fade |
| Skeleton 載入 | 1500ms | `linear` | Pulse 動畫循環 |
| 頁面切換 | 200ms | `ease-in-out` | Fade |

**減少動畫模式（`prefers-reduced-motion`）：**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 6.2 Loading States

| 場景 | 載入方式 | 說明 |
|------|----------|------|
| 頁面初次載入 | Skeleton Screen | 模擬內容佈局，減少 Layout Shift |
| 資料刷新 | 細進度條（頂部） | 保留現有資料，避免閃爍 |
| 提交操作 | 按鈕 Spinner | 防止重複點擊，保留按鈕形狀 |
| 圖片載入 | 漸進式顯示（Blur → Clear） | 搭配低解析度佔位圖 |
| 無限捲動 | 底部 Spinner | 出現在已有內容下方 |

### 6.3 Feedback Patterns（操作反饋）

| 操作類型 | 反饋方式 | 顯示時間 |
|----------|----------|----------|
| 成功（儲存、刪除等） | Toast（綠色，右上角） | 3 秒後自動消失 |
| 警告（需確認的操作） | Confirmation Dialog | 使用者主動關閉 |
| 錯誤（API 失敗等） | Toast（紅色）+ 行內錯誤 | 5 秒或使用者關閉 |
| 複製到剪貼板 | Tooltip「已複製！」 | 2 秒後消失 |
| 表單驗證錯誤 | 行內錯誤訊息（紅色，欄位下方） | 直到修正 |
| 破壞性操作（刪除） | 確認 Dialog + 輸入確認文字 | 使用者主動確認 |

### 6.4 空狀態設計（Empty States）

每個列表/資料展示頁需設計空狀態：

- **插圖：** 輕量 SVG，傳達情境
- **標題：** 說明「現在是空的」（如「尚無任何訂單」）
- **說明：** 引導使用者下一步行動
- **CTA 按鈕：** 主要行動（如「建立第一筆訂單」）

---

## 附錄

### A. 設計 Token 來源

- Figma Variables：`{設計稿連結}`
- CSS Variables 輸出：`src/styles/tokens.css`
- Tailwind 配置：`tailwind.config.ts`

### B. 瀏覽器測試矩陣

| 瀏覽器 | 版本 | 作業系統 | 優先級 |
|--------|------|----------|--------|
| Chrome | 最新 2 版 | Windows, macOS | P0 |
| Safari | 最新 2 版 | macOS, iOS | P0 |
| Firefox | 最新 2 版 | Windows, macOS | P1 |
| Edge | 最新 2 版 | Windows | P1 |
| Chrome Mobile | 最新版 | Android | P1 |
| Samsung Browser | 最新版 | Android | P2 |

### C. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | <!-- TODO: YYYY-MM-DD --> | 初版建立 | <!-- TODO --> |

### D. 相關文件

- [`SRS.md`](./SRS.md) — 軟體需求規格書（第 8 節介面規格）
- [`SDS.md`](./SDS.md) — 軟體設計規格書
- Figma 設計稿：<!-- TODO: 連結 -->
- Storybook：<!-- TODO: 連結 -->
