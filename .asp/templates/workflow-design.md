# 設計工作流範本

> 此 workflow 嵌入現有 ADR → SDD → TDD 流程，在 ADR/SPEC 之後、SDD 之前新增設計階段。
> 由 `system_dev.md` Pre-Implementation Gate 步驟 4 觸發。

## 完整流程

```
ADR（為什麼）
  ↓ 架構影響時必須
SPEC 確認
  ↓
Design（設計階段）← 本文件（design: enabled 時）
  ↓ 設計確認後
SDD（如何設計）
  ↓
TDD（測試先行）
  ↓
實作
```

---

## 步驟 1：設計前準備

### 1.1 讀取 Design System

```
IF exists("design-system/MASTER.md"):
  READ("design-system/MASTER.md")
  READ("design-system/tokens.yaml")
ELSE:
  SUGGEST("先建立 design system 或使用 UI/UX Skill 產生")
```

### 1.2 確認頁面是否有專屬規格

```
IF exists("design-system/pages/{page-name}.md"):
  READ → 頁面級規則優先於 MASTER.md
```

### 1.3 確認 SDD 產出物

從 `docs/specs/` 確認：

- [ ] 業務需求 → 知道頁面目的
- [ ] Data Model → 知道要呈現什麼資料
- [ ] API Spec → 知道資料結構和欄位

---

## 步驟 2：設計執行

根據專案使用的工具選擇路徑：

### 路徑 A：使用設計 MCP（Pencil / Paper 等）

1. 讀取 design system 作為 context
2. 在設計工具中建立頁面/元件
3. 遵循 design tokens（色彩、間距、字型）
4. 處理所有必要狀態（loading / empty / error / success）

### 路徑 B：純 Claude Code（直接產出程式碼）

1. 讀取 design system 和 API spec
2. 直接生成前端程式碼
3. 色彩使用 token 對應的 class（不用 magic number）
4. 響應式：桌面優先，支援平板

---

## 步驟 3：設計 Review

### Review 檢查清單

```markdown
### 一致性
- [ ] 色彩符合 design tokens 定義
- [ ] 間距遵循 grid system
- [ ] 字型使用正確的 family / size / weight
- [ ] 圓角使用定義的 scale

### 完整性
- [ ] 包含所有必要的元件狀態（loading, empty, error）
- [ ] 互動狀態完整（hover, focus, active, disabled）
- [ ] 包含 dark mode（若適用）

### 可用性
- [ ] 資訊層級清晰（5 秒法則）
- [ ] 操作路徑直覺（3 步內完成常見操作）
- [ ] 危險操作有確認流程
```

### 如果 Review 發現新 Pattern

```
1. 更新 design-system/MASTER.md 的元件清單
2. 如果是頁面特有規則，新增 design-system/pages/{page-name}.md
3. 提交 Git
```

---

## 步驟 4：Design-to-Code Handoff

設計確認後，提取實作所需資訊：

1. **提取 Design Token** → 對應到 CSS 變數或 Tailwind config
2. **提取元件結構** → 對應到前端元件清單
3. **提取佈局資訊** → 對應到 CSS layout（flex/grid）

### 與 OpenAPI 連動（design + openapi 同時啟用時）

設計稿中的資料需求推導 API 契約：

```
畫面元素       → 資料需求          → OpenAPI Schema
用戶列表       → GET /users        → User[]
表單提交       → POST /users       → CreateUserRequest
```

流程：設計確認 → 提取資料需求 → openapi_gate() → SDD → TDD → 實作

---

## 步驟 5：交接到 TDD

設計決策轉化為可測試的驗收條件：

```
設計決策                        → 測試條件
「統計卡片有 4 張」              → 測試渲染 4 個 StatsCard
「事件數 > 5 時卡片變紅」        → 測試條件渲染對應色彩
「API 失敗顯示重試按鈕」         → 測試 error 狀態 UI
```

---

## 常見情境速查

### 新頁面

```
1. 讀取 MASTER.md
2. 確認使用者角色和主要操作
3. 選擇佈局模式
4. 設計 → Review → 交接 TDD
```

### 修改現有元件

```
1. 讀取 MASTER.md + component specs
2. 確認修改範圍
3. 保持與現有 design system 一致
4. 更新 component specs（如有新變體/狀態）
```

### 整頁重構（對齊 Design System）

```
1. 讀取 MASTER.md + tokens
2. 對比目前實作和設計規範
3. 列出不符合的項目
4. 逐一修正，每次確認
```
