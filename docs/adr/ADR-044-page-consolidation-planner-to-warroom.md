# [ADR-044]: page-consolidation-planner-to-warroom

| 欄位 | 內容 |
|------|------|
| **狀態** | `Accepted` |
| **日期** | 2026-03-24 |
| **決策者** | Frontend Team |

---

## 背景（Context）

Planner (/planner) and War Room (/warroom) had significant feature overlap: both contained OODA cycle controls, target management, and operational dashboards. The ATT&CK technique matrix and attack graph were buried as tabs inside Planner, making them hard to discover. This created UX confusion about which page to use for tactical operations.

---

## 評估選項（Options Considered）

### 選項 A：Keep both pages, deduplicate features

- **優點**：No navigation changes, less migration risk
- **缺點**：Still two pages for overlapping concerns; maintenance burden
- **風險**：Continued user confusion

### 選項 B：Remove /planner, merge into War Room + extract ATT&CK

- **優點**：Single operations hub; ATT&CK gets dedicated visibility; cleaner nav
- **缺點**：Migration effort; redirect needed for bookmarks
- **風險**：Temporary disruption for users with /planner bookmarks (mitigated by redirect)

---

## 決策（Decision）

We choose **Option B**: Remove /planner as a standalone page, merge target management into War Room tabs (timeline + mission), and extract ATT&CK matrix/graph to a new dedicated route /attack-surface.

The /planner route now redirects to /warroom to preserve existing bookmarks and links.

---

## 後果（Consequences）

**正面影響：**
- Navigation stays at 5 items (operations, war room, attack surface, vulns, tools)
- Single operations hub in War Room reduces context-switching
- ATT&CK surface gets top-level visibility for security analysts
- Cleaner UX with less feature duplication

**負面影響 / 技術債：**
- Planner components (MissionTab, AttackTab, AttackGraphTab) may need cleanup if no longer referenced
- Old /planner deep links with ?tab= parameters will lose tab context on redirect

**後續追蹤：**
- [ ] Remove unused Planner components after War Room and Attack Surface pages are complete
- [ ] Update documentation and user guides referencing /planner
- [ ] Clean up Planner-specific i18n keys once migration is verified

---

## 成功指標（Success Metrics）

| 指標 | 目標值 | 驗證方式 | 檢查時間 |
|------|--------|----------|----------|
| Build passes | 0 errors | `make build` | PR merge |
| i18n parity | 0 missing keys | `make i18n-check` | PR merge |
| /planner redirect works | 302 to /warroom | Manual test | After deploy |
| Nav item count | 5 items | Visual check | After deploy |

---

## 關聯（Relations）

- 取代：（無）
- 被取代：（無）
- 參考：Page consolidation task for Athena frontend
