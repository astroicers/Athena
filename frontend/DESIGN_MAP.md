# Design Map — .pen Frame ↔ Frontend Code

> Updated: 2026-03-20 — Deep Gemstone v3 Design System
> Design file: `design/pencil-new-v2.pen`（唯一真相來源）

## Navigation (5 routes)

| Route | Page Name | Main File | Status |
|-------|-----------|-----------|--------|
| `/operations` | Operations | `app/operations/page.tsx` | Active |
| `/planner` | Planner (3 tabs: Mission / ATT&CK / Attack Graph) | `app/planner/page.tsx` | Active |
| `/warroom` | War Room (Campaign Timeline + Status Panel) | `app/warroom/page.tsx` | Active |
| `/vulns` | Vulnerabilities (+ PoC Evidence panel) | `app/vulns/page.tsx` | Active |
| `/tools` | Tool Registry | `app/tools/page.tsx` | Active |

### Merged Routes (redirect to parent)

| Old Route | Redirects To | Redirect File |
|-----------|-------------|---------------|
| `/attack-graph` | `/planner?tab=attack-graph` | `app/attack-graph/page.tsx` |
| `/poc` | `/vulns` | `app/poc/page.tsx` |
| `/opsec` | `/warroom` | `app/opsec/page.tsx` |
| `/decisions` | `/warroom` | `app/decisions/page.tsx` |

## .pen Frame ID 對應表

| Frame ID | 名稱 | 位置 (x, y) | Route |
|----------|------|------------|-------|
| `ItHzi` | Operations | (0, 0) | `/operations` |
| `dUlxq` | Planner - Mission Tab | (1640, 0) | `/planner` |
| `XP8YS` | Planner - ATT&CK Tab | (3280, 0) | `/planner?tab=attack` |
| `2qyS3` | Planner - Attack Graph Tab | (0, 1000) | `/planner?tab=attack-graph` |
| `OoOXX` | War Room | (1640, 1000) | `/warroom` |
| `EEbwu` | War Room — OPSEC Detail | (3280, 1000) | `/warroom` (inline) |
| `Nntpe` | War Room — Decision Detail | (0, 2000) | `/warroom` (inline) |
| `avyIZ` | Vulnerability Dashboard | (1640, 2000) | `/vulns` |
| `EMRMB` | Tools - Registry | (3280, 2000) | `/tools` |
| `tCMir` | NotificationCenter | (0, 3000) | modal overlay |

### Design System Frames

| Frame ID | 名稱 | 位置 (x, y) |
|----------|------|------------|
| `ukJKX` | Design Tokens | (5200, 0) |
| `18nk0` | Icons | (5200, 2600) |
| `keVgf` | Atoms | (5200, 3900) |
| `c4rJq` | Composites | (5200, 7200) |

## War Room 新架構

```
┌─ Sidebar ─┬─── Campaign Timeline (scrollable) ───┬─ Status Panel ─┐
│ 200px     │ Recon → OODA#1 → Directive →          │ C5ISR Health  │
│ icon+label│ OODA#2 → Directive →                   │ Noise / Risk  │
│           │ OODA#3 (active) →                      │ Decision: GO  │
│           │ Mission Objective                      │ Confidence    │
└───────────┴────────────────────────────────────────┴───────────────┘
```

## Sidebar Navigation (5 items, 200px with labels)

```
Operations  →  /operations    (layout-grid icon)
Planner     →  /planner       (flag icon)
War Room    →  /warroom       (activity icon)
Vulns       →  /vulns         (bug icon)
Tools       →  /tools         (settings icon)
```

Defined in `src/lib/constants.ts` → `NAV_ITEMS`.

## Design Token Trust Chain

```
pen → tokens.yaml → globals.css → tailwind.config → code
```

JS token constants: `src/lib/designTokens.ts`
