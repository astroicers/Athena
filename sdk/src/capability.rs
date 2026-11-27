// SPDX-License-Identifier: Apache-2.0
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// One attack capability: which MSF module to use for a matched service, persisted in
/// the `attack_capabilities` table.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttackCapability {
    pub id: Uuid,
    /// Match grammar (replicates the old hardcoded boolean logic, first-match-by-priority):
    /// OR-clauses separated by `||`; AND-terms within a clause by `&&`; a term is either
    /// `port:<N>` (matches an open-port fact `<N>/...`) or a substring tested against
    /// lower-cased `service.*.version` facts. e.g. `samba && 3.0 || samba && 3.x`.
    pub service_match: String,
    /// MSF module path WITHOUT type prefix, e.g. `unix/ftp/vsftpd_234_backdoor`.
    pub module: String,
    /// `exploit` | `auxiliary` | `post`.
    pub tool_type: String,
    pub default_payload: String,
    /// Extra module options merged into the call, e.g. `{"RPORT":21}`.
    pub default_options: serde_json::Value,
    pub mitre: String,
    pub params_hint: String,
    /// Login/brute modules need USERNAME/PASSWORD options.
    pub requires_creds: bool,
    /// Reverse-payload modules need the ADR-140 callback channel.
    pub needs_channel: bool,
    /// Higher = preferred when multiple rows match (first-match order of the old ladder).
    pub priority: i32,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl AttackCapability {
    /// Does this capability's `service_match` match the observed (lower-cased) version
    /// strings / open-port strings? Implements the `||` / `&&` / `port:` grammar.
    pub fn matches(&self, versions: &[String], ports: &[String]) -> bool {
        self.service_match.split("||").any(|clause| {
            let mut any_term = false;
            let all = clause.split("&&").all(|term| {
                let term = term.trim();
                if term.is_empty() {
                    return false;
                }
                any_term = true;
                if let Some(port) = term.strip_prefix("port:") {
                    let prefix = format!("{}/", port.trim());
                    ports.iter().any(|p| p.starts_with(&prefix))
                } else {
                    versions.iter().any(|v| v.contains(term))
                }
            });
            any_term && all
        })
    }
}
// ─────────────────────────────────────────────────────────────────────────────
// Payload noise classification (ADR-159 §A) — pure data contract.
//
// Single source of truth for "how loud is this payload on the wire", shared by the
// opsec budget path (athena-act consumes `cost()` on a landed shell, ADR-159 §D),
// the `DetectionScorer` (athena-capability, within-priority-tier noise bias), and
// ORIENT's payload-selection trade-off injection. It lives in the 0th-layer types
// crate (zero `athena-*` dep) precisely so all three consumers share it WITHOUT
// depending on each other (athena-capability / athena-orient depend only on
// athena-types; athena-act maps the cost into `consume_budget`). Mirrors the
// existing substring-classifier precedent `payload_needs_wait_floor` in athena-act
// (documented near-duplicate; consolidation deferred to avoid widening the diff).
// ─────────────────────────────────────────────────────────────────────────────

/// How detectable a payload is on the wire, derived PURELY from its MSF payload
/// string. Ordered quiet→loud; the numeric [`NoiseClass::cost`] feeds both the opsec
/// noise budget and the `DetectionScorer` penalty.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NoiseClass {
    /// Raw command exec, no session, no callback (e.g. `cmd/unix/interact`). Quietest.
    Quiet,
    /// Single shell callback / listener (e.g. `cmd/unix/reverse`, bind shells).
    Moderate,
    /// Staged in-memory implant — large stage transfer, distinctive on-wire
    /// (e.g. `*/meterpreter/*`).
    Loud,
    /// External C2 / staged loader (beacon, Cobalt-style). Loudest.
    Blaring,
}

impl NoiseClass {
    /// Noise/detection cost in opsec budget points. `Quiet=1 … Blaring=10`.
    /// Bounded small so a single `DetectionScorer` contribution stays well under the
    /// dominance cap (`cost*DETECTION_PENALTY_PER_COST` ≤ one priority unit).
    pub const fn cost(self) -> i32 {
        match self {
            NoiseClass::Quiet => 1,
            NoiseClass::Moderate => 3,
            NoiseClass::Loud => 6,
            NoiseClass::Blaring => 10,
        }
    }
}

/// Classify an MSF payload string by on-wire noise (ADR-159 §A). Pure, substring,
/// MOST-SPECIFIC-FIRST: `beacon`/`cobalt`/`stager`/`staged` (Blaring) is tested
/// BEFORE `meterpreter` (Loud) BEFORE `reverse`/`bind`/`c2` (Moderate), so a
/// `*/meterpreter/reverse_tcp` classifies `Loud` — never `Moderate`. Unknown / empty
/// / raw `interact` → `Quiet` (fail-quiet: never over-penalize an unrecognized
/// payload string).
pub fn payload_noise_cost(payload: &str) -> NoiseClass {
    let p = payload.to_ascii_lowercase();
    if p.contains("beacon") || p.contains("cobalt") || p.contains("stager") || p.contains("staged") {
        NoiseClass::Blaring
    } else if p.contains("meterpreter") {
        NoiseClass::Loud
    } else if p.contains("reverse") || p.contains("bind") || p.contains("c2") {
        NoiseClass::Moderate
    } else {
        NoiseClass::Quiet
    }
}

/// Operator opsec preference fed into capability selection (ADR-159 §B).
/// `stealth_level` scales the `DetectionScorer` penalty: `0.0` = noise-blind
/// (DEFAULT — a behaviour-preserving no-op; the scorer then contributes exactly
/// `0.0`), `1.0` = maximally stealth-biased. Sourced from
/// `config.compliance.selection_stealth_level`.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize)]
pub struct OpsecPref {
    /// `0.0` (default) … `1.0`. Clamped at scoring time.
    pub stealth_level: f64,
}

// ─────────────────────────────────────────────────────────────────────────────
// Capability selection — pure data contract (ADR-143).
//
// These traits + types are the *contract* between the selection configuration /
// composite scorer (which live in the 2nd-layer `athena-capability` crate) and the
// callers (ACT router / ORIENT). They carry ZERO business logic and ZERO `athena-*`
// dependency beyond this crate, so they legitimately live in the 0th-layer types
// crate (ADR-134 §1/§3, mirroring `CapabilityRepository`). The concrete
// `CompositeSelector` + 4 scorers live in `athena-capability` and are injected as
// `Arc<dyn CapabilitySelector>` by main.rs (10th layer) — `EngineContext` only ever
// holds the trait object, never names the concrete selector.
// ─────────────────────────────────────────────────────────────────────────────

/// Aggregate trust summary over the facts supporting a selection (ADR-142a).
///
/// Semantic: an aggregate of `FactProvenance::rank()` over the supporting facts.
/// `lowest_rank` is the minimum trust rank observed (1 = `Scan`/`ShellOutput`, the
/// least-trusted, target-controllable classes). `fact_count == 0` means *empty /
/// neutral* — in which case `RiskScorer` MUST contribute `weight == 0.0` (required
/// for the behaviour-equivalence test). The summary is computed once, before
/// scoring, so every scorer stays a pure function.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FactTrustSummary {
    /// Number of supporting facts aggregated. 0 ⇒ neutral ⇒ no risk penalty.
    pub fact_count: usize,
    /// Minimum `FactProvenance::rank()` across supporting facts (lower = less trusted).
    /// `None` when `fact_count == 0`.
    pub lowest_rank: Option<u8>,
}

/// Outcome of a previously-attempted capability within *this* operation.
///
/// v1 placeholder: there is no in-op module-keyed outcome signal available
/// (failed exploits emit no fact; landing facts carry no module identity), so
/// `SelectionContext.history` is ALWAYS empty in v1 and `HistoryScorer` is a no-op.
/// Real history is DEFERRED to v2 (needs an outcome-persistence write-path +
/// technique→module map, a separate Accepted ADR). The field exists so the contract
/// is forward-compatible without a v2 type churn.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityOutcome {
    /// MSF module path the outcome belongs to.
    pub module: String,
    /// Whether the prior attempt succeeded.
    pub success: bool,
}

/// Everything a scorer needs, filled once before scoring ⇒ scorers are pure
/// functions (deterministic, fast on the ORIENT/ACT hot path, unit-testable).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SelectionContext {
    /// Lower-cased `service.*.version` strings observed for the operation.
    pub versions: Vec<String>,
    /// Lower-cased open-port strings (e.g. `3632/tcp/distccd`).
    pub ports: Vec<String>,
    /// Deployment channel availability (config-driven, default true ⇒ fail-open).
    /// Orthogonal to per-row `AttackCapability.needs_channel`.
    pub channel_available: bool,
    /// Aggregated source trust over supporting facts (empty ⇒ no risk penalty).
    pub fact_trust: FactTrustSummary,
    /// In-op outcomes (v1: ALWAYS empty — see `CapabilityOutcome`).
    pub history: Vec<CapabilityOutcome>,
    /// Operator opsec preference (ADR-159 §B). Default (`stealth_level == 0.0`) ⇒
    /// `DetectionScorer` is a no-op, so legacy ordering is preserved byte-for-byte.
    pub opsec_pref: OpsecPref,
}

/// One scorer's contribution for one candidate. Combination operator is an
/// additive sum of `weight`; a neutral contribution is exactly `0.0`. `veto` is
/// NOT a negative weight — a vetoed candidate is excluded *before* summation
/// (but still recorded in the trace with its reason).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreContribution {
    /// Additive weight (bounded `|weight| <= 100.0` by the dominance invariant).
    pub weight: f64,
    /// Hard exclusion from selection (still traced). NOT a negative weight.
    pub veto: bool,
    /// Human-readable explanation, fed into the selection trace.
    pub reason: String,
}

/// One scorer's line in the per-candidate trace.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScorerLine {
    pub name: String,
    pub weight: f64,
    pub reason: String,
}

/// One candidate's scored row in the selection trace.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredCandidate {
    pub module: String,
    pub total: f64,
    pub vetoed: bool,
    pub per_scorer: Vec<ScorerLine>,
}

/// Explainable record of a selection: which module won + every candidate's score
/// breakdown. Written to PhaseContext.extensions under the sibling key
/// `"selection_trace"` (NOT merged into the technique-keyed `decision_trace`).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SelectionTrace {
    /// Winning module, or `None` when no candidate survived (all vetoed / no match).
    pub chosen: Option<String>,
    /// Every candidate, with its total and per-scorer breakdown.
    pub candidates: Vec<ScoredCandidate>,
}

/// A single scorer: a pure function from `(candidate, context)` to a contribution.
/// Implementations live in `athena-capability` (2nd layer); this is the contract.
pub trait CapabilityScorer: Send + Sync {
    /// Stable name for tracing (e.g. `"match_specificity"`).
    fn name(&self) -> &str;
    /// Score one candidate against the context. Pure, deterministic.
    fn score(&self, cap: &AttackCapability, ctx: &SelectionContext) -> ScoreContribution;
}

/// Selects the single best capability for an observation, with a full trace.
/// The concrete `CompositeSelector` (4 scorers) lives in `athena-capability`;
/// `EngineContext` holds only `Arc<dyn CapabilitySelector>` and never names it.
pub trait CapabilitySelector: Send + Sync {
    /// Choose the best non-vetoed candidate (highest total) and emit the trace.
    /// Returns `(None, trace)` when no candidate survives.
    fn select(
        &self,
        candidates: &[AttackCapability],
        ctx: &SelectionContext,
    ) -> (Option<AttackCapability>, SelectionTrace);
}

#[cfg(test)]
mod noise_tests {
    use super::{NoiseClass, OpsecPref, SelectionContext, payload_noise_cost};

    #[test]
    fn cost_is_monotonic_quiet_to_blaring() {
        assert!(NoiseClass::Quiet.cost() < NoiseClass::Moderate.cost());
        assert!(NoiseClass::Moderate.cost() < NoiseClass::Loud.cost());
        assert!(NoiseClass::Loud.cost() < NoiseClass::Blaring.cost());
        assert_eq!(NoiseClass::Quiet.cost(), 1);
        assert_eq!(NoiseClass::Blaring.cost(), 10);
    }

    #[test]
    fn raw_and_interact_are_quiet() {
        assert_eq!(payload_noise_cost("cmd/unix/interact"), NoiseClass::Quiet);
        assert_eq!(payload_noise_cost("cmd/unix/generic"), NoiseClass::Quiet);
    }

    #[test]
    fn reverse_and_bind_are_moderate() {
        assert_eq!(payload_noise_cost("cmd/unix/reverse"), NoiseClass::Moderate);
        assert_eq!(payload_noise_cost("cmd/unix/bind_perl"), NoiseClass::Moderate);
    }

    #[test]
    fn meterpreter_is_loud_and_beats_reverse_in_match_order() {
        // The load-bearing ordering case: `*/meterpreter/reverse_tcp` contains BOTH
        // "meterpreter" and "reverse" — most-specific-first MUST classify it Loud.
        assert_eq!(payload_noise_cost("java/meterpreter/reverse_tcp"), NoiseClass::Loud);
        assert_eq!(payload_noise_cost("linux/x86/meterpreter/bind_tcp"), NoiseClass::Loud);
    }

    #[test]
    fn beacon_and_stager_are_blaring_and_beat_meterpreter() {
        assert_eq!(payload_noise_cost("windows/x64/cobalt_beacon"), NoiseClass::Blaring);
        // A meterpreter STAGER must classify Blaring (stager tested before meterpreter).
        assert_eq!(payload_noise_cost("windows/meterpreter/reverse_https_stager"), NoiseClass::Blaring);
    }

    #[test]
    fn unknown_and_empty_fail_quiet() {
        assert_eq!(payload_noise_cost(""), NoiseClass::Quiet);
        assert_eq!(payload_noise_cost("some/novel/payload_name"), NoiseClass::Quiet);
    }

    #[test]
    fn case_insensitive() {
        assert_eq!(payload_noise_cost("JAVA/METERPRETER/REVERSE_TCP"), NoiseClass::Loud);
    }

    #[test]
    fn opsec_pref_and_selection_context_default_is_noise_blind() {
        assert_eq!(OpsecPref::default().stealth_level, 0.0);
        // SelectionContext::default() must carry stealth 0.0 (behaviour-preserving).
        assert_eq!(SelectionContext::default().opsec_pref.stealth_level, 0.0);
    }
}
