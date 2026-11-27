// SPDX-License-Identifier: Apache-2.0
//! ADR-171 pure-stable public-surface witness (grill #7 — no cargo-public-api / nightly in Phase 1).
//! Binds the v0.1 contract signatures so any breaking change to a re-exported trait or its data
//! types fails to COMPILE here. Together with the compile-time conformance of
//! `athena-sdk-example-scorer` (which implements `CapabilityScorer` through this crate), this is
//! the local forcing function that replaces the published-SDK conformance CI until Phase 2.

use athena_sdk::{
    AthenaError, AttackCapability, CapabilityScorer, CapabilitySelector, DecisionEngine,
    ExecutionOutcome, Fact, FactValue, OodaIterationId, OperationId, PhaseContext, ScoreContribution,
    SelectionContext, SelectionTrace,
};

// CapabilityScorer signature witness — changing `name`/`score` breaks this line.
fn _scorer_witness<S: CapabilityScorer>(
    s: &S,
    cap: &AttackCapability,
    ctx: &SelectionContext,
) -> ScoreContribution {
    let _name: &str = s.name();
    s.score(cap, ctx)
}

// CapabilitySelector must stay object-safe (core holds it as `Arc<dyn CapabilitySelector>`).
fn _selector_object_safe(_: &dyn CapabilitySelector) {}

// CapabilitySelector::select signature witness.
fn _selector_witness<S: CapabilitySelector>(
    s: &S,
    cands: &[AttackCapability],
    ctx: &SelectionContext,
) -> (Option<AttackCapability>, SelectionTrace) {
    s.select(cands, ctx)
}

// DecisionEngine must stay object-safe (core holds it as `Arc<dyn DecisionEngine>`).
fn _engine_object_safe(_: &dyn DecisionEngine) {}

// DecisionEngine async-signature witness — changing `name`/`run_iteration`/`abort`
// (or their argument/return types) breaks this. `run_with_context` has a default impl.
#[allow(dead_code)]
async fn _engine_witness<E: DecisionEngine>(e: &E, op: &OperationId) {
    let _name: &'static str = e.name();
    let _run: Result<(OodaIterationId, ExecutionOutcome), AthenaError> = e.run_iteration(op).await;
    let _abort: Result<(), AthenaError> = e.abort(op).await;
}

// Presence witnesses for re-exported data types (compile-time only).
#[allow(dead_code)]
fn _data_types(
    _: &Fact,
    _: &FactValue,
    _: &PhaseContext,
    _: &OperationId,
    _: &OodaIterationId,
    _: &ExecutionOutcome,
    _: &AthenaError,
) {
}

#[test]
fn v0_1_surface_compiles() {
    // The witnesses above are the real assertions (compile-time). This anchors them as a test.
}
