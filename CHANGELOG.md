# Changelog

All notable changes to `athena-sdk` are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/); versioning: [SemVer](https://semver.org/)
(0.x pre-1.0 — the contract may break between 0.x releases).

## [0.1.0] - Unreleased

### Added
- Initial contract surface (Phase 1 facade over `athena-types`):
  - Traits: `CapabilityScorer`, `CapabilitySelector`, `DecisionEngine`
    (full `DecisionEngine` integration is roadmap — needs WASM / MCP-over-protocol).
  - Data types: `Fact`, `FactValue`, `PhaseContext`, `OperationId`, `OodaIterationId`,
    `ExecutionOutcome`, `AthenaError`, `ErrorClass`, and scorer/selector supporting types
    (`AttackCapability`, `SelectionContext`, `ScoreContribution`, `SelectionTrace`, …).
- Runnable examples (each depends only on `athena-sdk`, no core crates):
  `quiet_scorer`, `weighted_scorer`, `multi_factor_scorer` (`CapabilityScorer`s),
  `composite_selector` (a custom `CapabilitySelector` composing scorers), and
  `decision_engine_concept` (illustrative `DecisionEngine` shape — full integration is roadmap).
- Compile-time contract witness for `DecisionEngine` (name/run_iteration/abort) in
  `tests/surface.rs`, matching the existing `CapabilityScorer`/`CapabilitySelector` witnesses.

_No contract-surface change: examples, tests, and docs only._

### Notes
- **Phase 2 canonical** — the v0.1 types are now DEFINED in this crate; `athena-sdk` is a
  zero-`athena-*` independently-compilable leaf (ADR-171 D2), and `athena-types` re-exports them so
  the core's `athena_types::X` paths are unchanged. Ready for independent publish once the legal
  placeholders are finalized (still human-gated).
- `LlmClient` / `KnowledgeBase` / `SkillsLoader` / `FactExtractor` remain roadmap.

## 1.0 commitment

`1.0` will be cut only after the surface is exercised by external modules and stabilized
(ADR-171 D4). Until then, treat every `0.x` bump as potentially breaking.
