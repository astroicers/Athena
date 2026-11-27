// SPDX-License-Identifier: Apache-2.0
//! # athena-sdk — Phase 2 (canonical)
//!
//! Stable Rust **contract traits + data types** for building hot-pluggable modules for Athena's
//! OODA loop **without** the core source. In Phase 2 (canonical) the v0.1 contract types are
//! **defined here** (not re-exported from a private crate), so `athena-sdk` is a **zero-`athena-*`
//! dependency leaf** that compiles/publishes independently (ADR-171 D2). `athena-types` (private,
//! part of the BSL core) re-exports these types, so the core keeps its `athena_types::X` paths.
//!
//! Licensed **Apache-2.0** (SPDX header per file). A BSL core depending on an Apache SDK is fine
//! (a permissive dependency consumed by a stricter license); this crate carries no BSL terms.
//!
//! ## Invariant
//! This crate **must not** depend on any `athena-*` crate (enforced by `tests/boundary.rs`). Do not
//! add `use athena_types::…` here or in tests — that would create a cycle.
//!
//! ## v0.1 surface
//! - Decision contracts: [`CapabilityScorer`], [`CapabilitySelector`], [`DecisionEngine`]
//!   (full `DecisionEngine` integration is roadmap — needs WASM / MCP-over-protocol, ADR-171).
//! - Supporting data types re-exported below.
//!
//! `LlmClient` / `KnowledgeBase` / `SkillsLoader` / `FactExtractor` remain roadmap (they live in
//! impl crates and need a contract/impl split first).
//!
//! ## ADR-101 note
//! ADR-171 D1 (SDK is the contract-layer crate) governs this multi-trait crate, superseding
//! ADR-101's one-trait-per-crate rule for this boundary crate.

mod capability;
mod decision;
mod engine;
mod error;
mod fact;
mod operation;
mod phase_context;

// ── contract traits ─────────────────────────────────────────────────────────
pub use capability::{CapabilityScorer, CapabilitySelector};
pub use engine::DecisionEngine;

// ── error / operation / phase ───────────────────────────────────────────────
pub use error::{AthenaError, ErrorClass};
pub use operation::OperationId;
pub use phase_context::PhaseContext;

// ── facts ───────────────────────────────────────────────────────────────────
pub use fact::{Fact, FactProvenance, FactTrait, FactValue};

// ── decision / execution ────────────────────────────────────────────────────
pub use decision::{
    Decision, ExecutionOutcome, ExecutionResult, OodaIterationId, OrientRecommendation, ToolCall,
};

// ── scorer / selector supporting types ──────────────────────────────────────
pub use capability::{
    payload_noise_cost, AttackCapability, CapabilityOutcome, FactTrustSummary, NoiseClass,
    OpsecPref, ScoreContribution, ScoredCandidate, ScorerLine, SelectionContext, SelectionTrace,
};
