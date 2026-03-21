# [ADR-041]: Adopt Deep Gemstone v3 Design System

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-22 |
| **決策者** | 架構師 / 前端負責人 |

---

## 背景（Context）

Athena 前端存在 3 套互相衝突的色彩系統，導致 UI 不一致且維護困難：

1. **tokens.yaml 霓虹色系統**：早期定義的 neon-inspired palette，偏向高飽和度螢光色調
2. **globals.css 藍色系統**：前端 CSS 中獨立演化出的藍色調系統，與 tokens.yaml 脫鉤
3. **pen 設計稿系統**：設計師在 pencil-new.pen 中使用的第三套色彩，與前兩者均不一致

此外，Tailwind v4 改變了 `border-color` 的預設行為——自訂的 `border-athena-*` utility class 在 Tailwind v4 下無法正確套用顏色，導致邊框退化為瀏覽器預設灰色。這不是 Athena 的 bug，而是 Tailwind v4 的已知行為變更。

**核心問題：** 沒有單一真相來源（Single Source of Truth），三套系統各自演化，無法透過自動化工具驗證一致性。

---

## 評估選項（Options Considered）

### 選項 A：修補現有多系統（漸進統一）

- **優點**：改動範圍小，逐步收斂
- **缺點**：三套系統的映射關係複雜，容易漏改；無法解決 Tailwind v4 border 問題
- **風險**：持續存在 token 漂移，每次 UI 修改都需要手動對齊三處

### 選項 B：採用 Deep Gemstone v3 統一設計系統

- **優點**：
  - 單一真相來源（pen 設計稿），信任鏈清晰
  - 色票專為深色 UI 設計，高對比度且一致
  - 內建 Tailwind v4 workaround
  - 可透過 `make token-validate` / `make token-drift` 自動驗證
- **缺點**：
  - 需要一次性遷移所有 303+ hardcoded hex 值
  - pen 設計稿需完整重做（pencil-new.pen -> pencil-new-v2.pen）
- **風險**：大量 CSS 修改可能引入視覺回歸

### 選項 C：採用第三方設計系統（Radix/shadcn）

- **優點**：社群維護，生態成熟
- **缺點**：Athena 的軍事/滲透測試 UI 風格與通用設計系統差異太大；深色主題客製化工作量不亞於自建
- **風險**：受制於第三方更新週期

---

## 決策（Decision）

我們選擇 **選項 B：採用 Deep Gemstone v3 統一設計系統**，因為：

1. Athena 的 C2/War Room 深色 UI 需要專屬色票，通用設計系統無法滿足
2. 單一信任鏈能從根本解決 token 漂移問題
3. 自動化驗證工具（`make token-validate`、`make token-drift`）確保長期一致性

### Deep Gemstone v3 色票定義

| 用途 | 色彩名稱 | Hex 值 | CSS 變數 |
|------|----------|--------|----------|
| 主強調 | Sapphire Blue | `#1E6091` | `--color-accent` |
| 成功 | Emerald | `#059669` | `--color-success` |
| 警告 | Amber | `#B45309` | `--color-warning` |
| 錯誤 | Deep Red | `#B91C1C` | `--color-error` |
| 背景（最深） | Zinc Black | `#09090B` | `--color-bg-base` |
| 背景（卡片） | Zinc 900 | `#18181B` | `--color-bg-card` |
| 背景（懸停） | Zinc 800 | `#27272A` | `--color-bg-hover` |

### 信任鏈（Trust Chain）

```
pencil-new-v2.pen（唯一真相來源）
  → design-system/tokens.yaml（結構化定義）
    → frontend/src/styles/globals.css（CSS 變數）
      → frontend/tailwind.config.ts（Tailwind 擴展）
        → 前端代碼（消費端）
```

### Tailwind v4 Border Workaround

```tsx
// 禁止：Tailwind v4 下 border-athena-* 不套用顏色
className="border border-athena-accent"

// 正確：使用 CSS 變數直接引用
className="border border-[var(--color-accent)]"
```

### 其他設計規範

- **Border Radius**：統一 4px（`rounded`），禁止混用 `rounded-lg` / `rounded-xl`（除非 pen 設計稿明確指定）
- **字型**：JetBrains Mono（主要/代碼）、Inter（輔助/正文）
- **字型大小**：遵循 pen 設計稿定義，不自行發明尺寸

---

## 後果（Consequences）

**正面影響：**
- UI 色彩一致性得到根本性解決，消除三套系統衝突
- `make token-validate` 可在 CI 中自動偵測 token 不一致
- `make token-drift` 可偵測前端代碼中殘留的 hardcoded hex 值
- Tailwind v4 border 問題有明確的 workaround 策略
- 新增組件時有清晰的色彩參考，降低決策成本

**負面影響 / 技術債：**
- 一次性遷移 303+ hardcoded hex 值（已完成 Wave 1-3）
- `border-athena-*` class 全面禁用，需要開發者習慣改變
- pen 設計稿需從 pencil-new.pen 遷移到 pencil-new-v2.pen

**後續追蹤：**
- [x] Wave 1-3 色彩遷移完成（303 個 hex 值替換為 CSS vars/Tailwind classes）
- [x] SPEC-051 更新：Design Token 與 pen 同步協議
- [ ] CI 整合 `make token-validate`（PR check）
- [ ] CI 整合 `make token-drift`（PR check，warning level）
- [ ] 前端 lint 規則：禁止 `border-athena-*` class

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Token 一致性 | `make token-validate` 零錯誤 | CI check | 每次 PR |
| Hardcoded hex 殘留 | `make token-drift` 零新增 | CI check | 每次 PR |
| `border-athena-*` 使用 | 零使用 | `grep -r "border-athena"` | 遷移完成時 |
| 視覺回歸 | pen 設計稿與瀏覽器 100% 一致 | 人工比對 | 遷移完成時 |

> 若遷移後發現 CSS 變數效能影響（CSSOM 渲染延遲 > 16ms），應重新評估是否需要 build-time token injection。

---

## 相關決策

### i18n 整合

Deep Gemstone v3 設計系統的所有 UI 文字必須遵循 i18n 規範（詳見 ADR-043）：

| 規則 | 說明 |
|------|------|
| **語言支援** | zh-TW（主要）+ en（備用） |
| **語言切換** | LocaleSwitcher 位於全域 header（PageHeader trailing slot） |
| **翻譯鍵** | War Room timeline 元件新增 27 個翻譯鍵 |
| **強制規範** | 所有 UI 文字必須使用 `useTranslations()` — 禁止 hardcoded 文字 |

---

## 關聯（Relations）

- 取代：無（首次統一設計系統決策）
- 被取代：無
- 參考：ADR-009（Frontend Component Architecture）、ADR-043（i18n Full Coverage with Locale Switcher）、SPEC-051（Design Token 與 pen 同步協議）
