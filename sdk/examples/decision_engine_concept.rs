// SPDX-License-Identifier: Apache-2.0
//! Minimal, self-contained example that depends ONLY on `athena-sdk`.
//!
//! Run: `cargo run --example decision_engine_concept`
//!
//! **Illustrative concept only.** Implements the `DecisionEngine` contract shape
//! so it compiles against the SDK, but does NOT drive a real OODA loop: a full
//! `DecisionEngine` that executes techniques needs a sandboxed, protocol-mediated
//! execution environment, which is on the roadmap and out of scope for a runnable
//! example. Here the async methods only prove the trait shape (they return an
//! empty outcome); `main` prints the engine's name and this caveat.

use async_trait::async_trait;
use athena_sdk::{AthenaError, DecisionEngine, ExecutionOutcome, OodaIterationId, OperationId};

/// A do-nothing engine. Real engines wire in Observe/Orient/Decide/Act phases
/// (private core) behind this same contract; this one just satisfies the shape.
struct ConceptEngine;

#[async_trait]
impl DecisionEngine for ConceptEngine {
    fn name(&self) -> &'static str {
        "concept_noop_engine"
    }

    /// Shape-only: returns a fresh iteration id and an empty outcome. A real
    /// engine would run one OODA iteration and report collected facts here.
    async fn run_iteration(
        &self,
        _op_id: &OperationId,
    ) -> Result<(OodaIterationId, ExecutionOutcome), AthenaError> {
        Ok((OodaIterationId::new(), ExecutionOutcome::default()))
    }

    async fn abort(&self, _op_id: &OperationId) -> Result<(), AthenaError> {
        Ok(())
    }
    // `run_with_context` uses the trait's default (delegates to `run_iteration`).
}

fn main() {
    let engine = ConceptEngine;
    println!("athena-sdk example — DecisionEngine `{}`", engine.name());
    println!("\n  這是 concept/illustrative 範例：只證明 trait 形狀能對著 SDK 編譯。");
    println!("  完整引擎整合＝roadmap，需沙箱 / 協定化執行環境，不在可跑範例的範圍內。");
    println!("\n→ 要驅動真實 OODA 迴圈的引擎屬私有核心；SDK 只公開這份可插拔契約。");
}
