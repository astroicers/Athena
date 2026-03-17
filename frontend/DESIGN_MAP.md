# Design Map — .pen Frame ↔ Frontend Code

> Auto-generated during page consolidation (2026-03-13).
> Update this file whenever design or routing changes.

## Navigation (Post-Consolidation: 9 → 5 pages)

| Route | Page Name | Main File | Status |
|-------|-----------|-----------|--------|
| `/operations` | Operations | `app/operations/page.tsx` | Active |
| `/planner` | Planner (3 tabs: Mission / ATT&CK / Attack Graph) | `app/planner/page.tsx` | Active |
| `/warroom` | War Room (+ OPSEC + Decisions panels) | `app/warroom/page.tsx` | Active |
| `/vulns` | Vulnerabilities (+ PoC Evidence panel) | `app/vulns/page.tsx` | Active |
| `/tools` | Tool Registry | `app/tools/page.tsx` | Active |

### Merged Routes (redirect to parent)

| Old Route | Redirects To | Redirect File |
|-----------|-------------|---------------|
| `/attack-graph` | `/planner?tab=attack-graph` | `app/attack-graph/page.tsx` |
| `/poc` | `/vulns` | `app/poc/page.tsx` |
| `/opsec` | `/warroom` | `app/opsec/page.tsx` |
| `/decisions` | `/warroom` | `app/decisions/page.tsx` |

## Component Extraction Map

| Original Page | Extracted Component | Location |
|--------------|---------------------|----------|
| `/attack-graph` | `AttackGraphTab` | `components/planner/AttackGraphTab.tsx` |
| `/poc` | `PocEvidencePanel` | `components/vulns/PocEvidencePanel.tsx` |
| `/opsec` | `OpsecPanel` | `components/warroom/OpsecPanel.tsx` |
| `/decisions` | `DecisionPanel` | `components/warroom/DecisionPanel.tsx` |

## .pen Frame ID 對應表

> 設計檔案：`design/pencil-new-v2.pen`（唯一真相來源）

| Frame ID | 名稱 | 位置 (x, y) | 狀態 |
|----------|------|------------|------|
| `ItHzi` | Operations | (0, 5000) | ✅ |
| `dUlxq` | Planner - Mission Tab | (0, 6000) | ✅ |
| `XP8YS` | Planner - ATT&CK Tab | (1540, 6000) | ✅ |
| `2qyS3` | Planner - Attack Graph Tab | (3080, 6000) | ✅ |
| `EMRMB` | Tools - Registry | (0, 7000) | ✅ |
| `avyIZ` | Vulnerability Dashboard | (0, 3000) | ✅ |
| `OoOXX` | War Room | (0, 8000) | ✅ |
| `EEbwu` | War Room V2 - OPSEC | (3080, 8000) | ✅ |
| `Nntpe` | War Room V2 - Decision | (4620, 8000) | ✅ |
| `fbLqg` | Attack Graph | (1540, 0) | ✅ |
| `OexrL` | Attack Graph - Credentials Tab | (3080, 0) | ✅ |
| `tCMir` | NotificationCenter | (0, 2000) | ✅ |
| `TNwwh` | NotificationCenter - Empty | (1540, 2000) | ✅ |
| `uSy6i` | PoC Report | (0, 4000) | ✅ |
| `k79tR` | PoC Report - Empty/Error | (1540, 4000) | ✅ |
| `lVZKT` | [DEPRECATED] OPSEC Dashboard | (0, 0) | 🏷️ |
| `nPItC` | [DEPRECATED] AI Decision Breakdown | (0, 1000) | 🏷️ |

## Key Dimensions (from .pen design v2)

| Element | Property | Value |
|---------|----------|-------|
| Operations card | height | 140px |
| War Room left panel (OODA) | width | 200px |
| War Room right panel (Action Log) | width | 300px |
| Planner TECHNIQUE column | width | 280px |
| Planner STATUS column | width | 100px |
| Attack Graph threat gauge | segment size | 24×12px (5 segments) |
| OPSEC metric card | height | 120px |
| OPSEC trend chart | height | 220px |

## Sidebar Navigation (5 items)

```
Operations  →  /operations
Planner     →  /planner
War Room    →  /warroom
Vulns       →  /vulns
Tools       →  /tools
```

Defined in `src/lib/constants.ts` → `NAV_ITEMS`.

## Design Token Quick Reference

> 完整定義見 `docs/specs/SPEC-051-design-token-and-pen-sync-protocol.md`

| 用途 | Token |
|------|-------|
| 頁面背景 | `#0a0e17` |
| 卡片背景 | `#111827` |
| 有內容卡片邊框 | `border-[#1f2937]` |
| 空狀態/低調邊框 | `border-white/5` |
| 輸入框邊框 | `border-[#1f2937]` |
| 主文字 | `#e5e7eb` |
| 次文字 | `#9ca3af` |
| 提示文字 | `#6b7280` |
| 字體 | `IBM Plex Mono` |

### 禁止模式

- ❌ `border border rounded`（缺色）
- ❌ `border-[#374151]`（用 `#1f2937`）
- ❌ `border-[#1f293740]`（用 `border-white/5` 或不帶 alpha）
- ❌ `items-end` on TabBar（用 `items-center`）

### 部署

```bash
# Docker 環境（正確）
docker compose build frontend && docker compose up -d frontend

# ❌ npx next start 在 Docker 環境下無效
```
