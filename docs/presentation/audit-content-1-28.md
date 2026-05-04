# Content Correctness Audit — Slides 1-28 (Cover / Doctrine / Architecture / Framework)

Source of truth: `/tmp/harry-pptx/ppt/slides/slide{1..28}.xml`
Converted markdown: `/Users/alexchih/Documents/Projects/Alex/Athena/docs/presentation/harry-chunks/01-cover-doctrine.md` (slides 1-20), `02-framework.md` (slides 21-28).

Method: read each PPTX XML and compare every textual run against the corresponding slidev block. Findings classified as **BLOCKER** (factual error, fabricated evidence, mistranslation that changes meaning) or **NICE-TO-FIX** (phrasing/cosmetic drift).

---

## Summary

| Metric | Count |
|---|---|
| Total slides audited | 28 |
| BLOCKER | 2 |
| NICE-TO-FIX | 6 |
| Clean (faithful) | 19 |
| TODO placeholder (skipped) | 1 (slide 3) |

**BLOCKER list:**
- Slide 12 — "三件事" but lists four OODA phases (mismatch between thesis and enumeration).
- Slide 15 — Fabricated `ops-log` panel with timestamps and metrics not present in XML.

---

## Per-slide findings

### Slide 1 — Cover (NICE-TO-FIX)

- XML header strip reads `// OPERATION FANCY-LEMUR-433FC2 :: CLASSIFIED`; md renames to `OPERATION ATHENA-433FC2`. Likely an intentional rebrand for the public talk, but flag for confirmation — if unintentional, restore `FANCY-LEMUR`.
- XML conference text is lowercase `Cybersec 2026`; md uppercases to `CYBERSEC 2026`. Cosmetic.
- XML status pill text reads only `全滅 全自動滲透`; md prepends `18m57s ·`. The `18m57s` value does live elsewhere on the slide (separate text run for the run-time stat), so combining them in one pill is a layout choice, not fabrication. OK.

### Slide 3 — TODO placeholder

Skipped per audit scope; current md is a planning placeholder, no XML comparison required.

### Slide 12 — Boyd's OODA origin (BLOCKER + NICE-TO-FIX)

- **BLOCKER**: md narrative says `Boyd 把 F-86 的勝利拆出三件事：觀察 — 判斷 — 決定 — 行動` — the sentence promises three items but enumerates four. XML left column reads `看見—判斷—決定—行動` (also four phases) without claiming "三件事". Either change `三件事` → `四件事`, or drop the count phrase entirely. As written it is internally contradictory.
- NICE-TO-FIX: md changes XML's `看見` to `觀察` in the dash list. Minor, but if the slide is teaching Boyd's vocabulary the original `看見` is closer to "see/observe-as-perception" and should probably be preserved.
- NICE-TO-FIX: XML bullets `MiG 速度快、火力強` simplified to `MiG 性能更好`; XML `F-86 卻贏 10:1 交換比` became `F-86 卻贏 10:1` (drops `交換比`). Recommend restoring the original specifics — the audience is technical and `交換比` (kill ratio) is the load-bearing term.
- NICE-TO-FIX: md right column adds descriptive sub-text under each OODA label (`節拍器，不是流程圖`, `Observe — 把外界訊號收進來`, `Orient — 用脈絡解讀`, `Decide — 在不確定下選一條`, `Act — 立即執行、立刻收回饋`). XML right column shows only the four labels in a circular diagram with no descriptions. Not fabricated *facts*, but added *narration* — flag in case the speaker wants the visual to stay minimal as in the original.

### Slide 13 — Athena = OODA mapping (NICE-TO-FIX)

- md ORIENT box reads `Claude LLM 讀取 facts → 輸出 recommended_technique + confidence`. XML reads `Claude LLM 讀取 facts + MITRE ATT&CK → 輸出 recommended_technique + confidence`. Restore the `+ MITRE ATT&CK` term — it's the differentiator that makes the orient step credible to a security audience.

### Slide 15 — Orient JSON (BLOCKER)

- **BLOCKER**: md adds an entire `<div class="ops-log">` panel with timestamps and metrics:
  ```
  [14:02:11] FACTS LOADED n=42
  [14:02:12] LLM CALL claude-opus
  [14:02:14] JSON PARSED ok
  [14:02:14] TECH PICKED T1558.004
  [14:02:14] CONFIDENCE 0.87
  [14:02:14] ROUTE READY asrep_roast
  [14:02:14] HANDOFF → DECIDE
  ```
  None of these lines exist in `slide15.xml`. The XML contains only the JSON code block (the orient output schema) plus the slide title/subtitle. Fabricating runtime telemetry is a credibility risk — at a security conference, audience members will assume those numbers come from a real run. Either delete the panel, or move the timestamps into a clearly-labelled "illustrative example" block backed by an actual replay log from the demo recording.

### Slides 2, 4-11, 14, 16-28 — Clean

Faithful transfer. Spot-checks on the items that matter for accuracy:

- Slide 8 metrics (Brier 0.31 → 0.12, composite confidence formula `(LLM × validation × history)^(1/3)`) — preserved verbatim.
- T-codes across slides 13-28 (T1558.004, T1649, T1003.003, T1110.002, T1046, T1059.003) — match XML.
- Fact category strings (`service.open_port`, `ad.user_no_preauth`, etc.) — match XML.
- Decision-engine pseudocode and engine_router branching (slides 21-24) — match XML.
- War-room iteration counts and the 18m57s run-time figure (slides 25-28) — match XML.

---

## Recommendation

Fix the two BLOCKERs before the talk:
1. Slide 12: reconcile `三件事` vs the four-item list.
2. Slide 15: remove or relabel the fabricated `ops-log` timestamps.

NICE-TO-FIX items are restoration of XML-original phrasing (`看見`, `MiG 速度快、火力強`, `10:1 交換比`, `+ MITRE ATT&CK`); ship-blocker only if the speaker wants strict fidelity to the original deck.
