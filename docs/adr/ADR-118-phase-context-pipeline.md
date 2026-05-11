# ADR-118: PhaseContext — Shared Pipeline State for OODA Phase Composition

**Status**: Draft
**Date**: 2026-05-11
**Deciders**: Project lead

---

## Context

The OODA pipeline in `athena-engine-ooda` hardwires data flow through three
fixed Rust structs:

```
ObservePhase → String (obs_summary)
             → OrientPhase → OrientRecommendation
                           → DecidePhase → Decision
                                         → ActPhase → ExecutionOutcome
```

This coupling has three operational consequences:

1. **Reordering phases requires rewriting trait signatures.** `DecidePhase::evaluate`
   takes `&OrientRecommendation` as its second parameter — moving Decide before
   Orient breaks the type chain at compile time.

2. **Adding a phase requires new intermediate types.** Inserting a `ValidatePhase`
   between Decide and Act means defining a new struct, changing `OodaEngine`'s
   field list, and adding a call in `run_iteration`.

3. **Operator overrides have no runtime pathway.** Layer-1 (ADR-109 compatible)
   introduced `OperatorDirectDecider` and `PassthroughOrient` as swappable
   implementations, but the API `operator_override` mode cannot yet wire them
   into a running operation — it only writes an audit fact. The pipeline topology
   is fixed at binary startup in `main.rs`.

These constraints conflict with red team operational reality, where:
- An operator may need to skip LLM orient mid-engagement (LLM unavailable,
  time pressure, or risk_score gate tripped)
- A new phase (e.g. human approval gate, OPSEC validation) may be needed for
  a specific engagement without recompiling the binary
- Extension data (e.g. "current foothold subnet", "confirmed credentials") must
  flow between phases without modifying existing trait signatures

---

## Decision

Introduce `PhaseContext` as the single value passed between OODA phases,
replacing the three separate intermediate types.

```rust
// athena-types/src/phase_context.rs
pub struct PhaseContext {
    pub op_id: OperationId,
    pub iter_id: OodaIterationId,

    // Produced by ObservePhase
    pub obs_summary: String,

    // Produced by OrientPhase (None until Orient runs)
    pub recommendation: Option<OrientRecommendation>,

    // Produced by DecidePhase (None until Decide runs)
    pub decision: Option<Decision>,

    // Free-form key-value store for operator overrides and inter-phase extensions
    // Keys: "operator_override_techniques", "operator_override_reason",
    //       "foothold_subnet", "confirmed_creds", etc.
    pub extensions: HashMap<String, serde_json::Value>,
}
```

Each phase trait is updated to accept and return `PhaseContext`:

```rust
pub trait ObservePhase: Send + Sync {
    async fn run(&self, ctx: PhaseContext) -> Result<PhaseContext, AthenaError>;
}
pub trait OrientPhase: Send + Sync {
    async fn run(&self, ctx: PhaseContext) -> Result<PhaseContext, AthenaError>;
}
pub trait DecidePhase: Send + Sync {
    async fn run(&self, ctx: PhaseContext) -> Result<PhaseContext, AthenaError>;
}
pub trait ActPhase: Send + Sync {
    async fn run(&self, ctx: PhaseContext) -> Result<PhaseContext, AthenaError>;
}
```

`OodaEngine::run_iteration` becomes:

```rust
let mut ctx = PhaseContext::new(op_id, iter_id);
ctx = self.observe.run(ctx).await?;
ctx = self.orient.run(ctx).await?;
ctx = self.decide.run(ctx).await?;
ctx = self.act.run(ctx).await?;
Ok((ctx.iter_id, ctx.into_outcome()))
```

`OperatorDirectDecider` reads `ctx.extensions["operator_override_techniques"]`
instead of ignoring `OrientRecommendation`, giving the API `operator_override`
mode a real execution pathway.

---

## Consequences

**Positive**
- Adding a phase = define a new trait + insert one `ctx = self.phase.run(ctx).await?;` line
- Removing a phase = delete that line; no downstream signature changes
- Extension bag allows inter-phase data without modifying structs
- `OperatorDirectDecider` can fully function: reads techniques from `ctx.extensions`
- Per-engagement pipeline configuration becomes feasible (layer-3 roadmap item)

**Negative / Trade-offs**
- All four phase trait signatures change → all existing implementations and mocks
  must be updated (estimated: ~12 files, ~200 lines changed)
- `PhaseContext` carries `Option<OrientRecommendation>` and `Option<Decision>` —
  phases must handle `None` defensively or panic at runtime rather than at compile time
- The `extensions` HashMap is untyped — miskeyed extensions are silent at compile time
- Test isolation is slightly harder: mocks must construct a full `PhaseContext`
  rather than accepting individual parameters

**Mitigations**
- Provide `PhaseContext::builder()` to reduce mock boilerplate
- Define `ctx.require_recommendation()` and `ctx.require_decision()` helpers that
  return `AthenaError::Internal` rather than panicking
- Add `#[non_exhaustive]` to extension key constants to catch typos at definition time

---

## Alternatives Considered

### A: Keep current struct chain, add `extensions: HashMap` to each intermediate type

Adds extensibility without changing trait signatures. Does not solve the reordering
or phase addition problem — the type chain is still rigid. Rejected because it
solves only one of the three stated problems.

### B: Use `Box<dyn Any>` for full dynamic dispatch between phases

Maximum flexibility, zero compile-time safety. Phases could pass any type to each
other without any schema. Rejected because the loss of type visibility makes audit
tracing and operator reasoning significantly harder.

### C: Keep existing architecture, add per-operation engine factory in API layer

`POST /api/operations` constructs a new `OodaEngine` with the appropriate phase
implementations wired in for each request. No trait signature changes needed.
Rejected because constructing an engine per request has non-trivial overhead
(KB init, skills loader, attack graph), and the AppState pattern would need
significant refactoring to expose individual phase constructors.

---

## Related ADRs

- ADR-109: `Arc<dyn Trait>` as hot-swap mechanism (this ADR extends it)
- ADR-112: DecisionEngine trait (unaffected — outer interface unchanged)
- Layer-1 implementation: commit `2aff774e` (OperatorDirectDecider, PassthroughOrient)
