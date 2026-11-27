// SPDX-License-Identifier: Apache-2.0
//! Minimal, self-contained example that depends ONLY on `athena-sdk`.
//!
//! Run: `cargo run --example composite_selector`
//!
//! Implements a custom `CapabilitySelector` that composes over several
//! `CapabilityScorer`s: for each candidate it sums every scorer's `weight`,
//! records a per-scorer trace line, honours any `veto`, then picks the
//! highest-scoring non-vetoed candidate. This is the shape a third party ships
//! when they want their own selection strategy on top of the SDK contract —
//! no core crate required.

use athena_sdk::{
    payload_noise_cost, AttackCapability, CapabilityScorer, CapabilitySelector, ScoreContribution,
    ScoredCandidate, ScorerLine, SelectionContext, SelectionTrace,
};
use chrono::Utc;
use uuid::Uuid;

/// Scorer 1: vetoes anything needing a noisy reverse callback channel.
struct QuietVeto;
impl CapabilityScorer for QuietVeto {
    fn name(&self) -> &str {
        "quiet_veto"
    }
    fn score(&self, cap: &AttackCapability, _ctx: &SelectionContext) -> ScoreContribution {
        if cap.needs_channel {
            ScoreContribution {
                weight: 0.0,
                veto: true,
                reason: "vetoed: needs reverse channel".into(),
            }
        } else {
            ScoreContribution {
                weight: 0.0,
                veto: false,
                reason: "quiet".into(),
            }
        }
    }
}

/// Scorer 2: prefers quieter payloads (a small negative weight per noise unit).
struct LowNoise;
impl CapabilityScorer for LowNoise {
    fn name(&self) -> &str {
        "low_noise"
    }
    fn score(&self, cap: &AttackCapability, _ctx: &SelectionContext) -> ScoreContribution {
        let noise = payload_noise_cost(&cap.default_payload);
        let weight = -(noise.cost() as f64);
        ScoreContribution {
            weight,
            veto: false,
            reason: format!("{noise:?} noise → {weight:+.1}"),
        }
    }
}

/// A selector composed of an ordered list of scorers. `total = base(priority) +
/// Σ weight`; a candidate vetoed by any scorer is excluded from the winner but
/// still appears in the trace.
struct MiniComposite {
    scorers: Vec<Box<dyn CapabilityScorer>>,
    priority_scale: f64,
}

impl MiniComposite {
    fn new(scorers: Vec<Box<dyn CapabilityScorer>>) -> Self {
        Self {
            scorers,
            priority_scale: 1000.0,
        }
    }
    fn base(&self, cap: &AttackCapability) -> f64 {
        self.priority_scale * cap.priority as f64
    }
}

impl CapabilitySelector for MiniComposite {
    fn select(
        &self,
        candidates: &[AttackCapability],
        ctx: &SelectionContext,
    ) -> (Option<AttackCapability>, SelectionTrace) {
        let mut scored: Vec<(usize, &AttackCapability, f64, bool, Vec<ScorerLine>)> =
            Vec::with_capacity(candidates.len());

        for (idx, cap) in candidates.iter().enumerate() {
            let mut per_scorer = Vec::with_capacity(self.scorers.len());
            let mut sum = 0.0;
            let mut vetoed = false;
            for scorer in &self.scorers {
                let c = scorer.score(cap, ctx);
                if c.veto {
                    vetoed = true;
                }
                sum += c.weight;
                per_scorer.push(ScorerLine {
                    name: scorer.name().to_string(),
                    weight: c.weight,
                    reason: c.reason,
                });
            }
            let total = self.base(cap) + sum;
            scored.push((idx, cap, total, vetoed, per_scorer));
        }

        // Highest total first; ties broken by original order (stable, deterministic).
        scored.sort_by(|a, b| {
            b.2.partial_cmp(&a.2)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });

        let chosen = scored
            .iter()
            .find(|(_, _, _, vetoed, _)| !*vetoed)
            .map(|(_, cap, _, _, _)| (*cap).clone());

        let trace = SelectionTrace {
            chosen: chosen.as_ref().map(|c| c.module.clone()),
            candidates: scored
                .iter()
                .map(|(_, cap, total, vetoed, per_scorer)| ScoredCandidate {
                    module: cap.module.clone(),
                    total: *total,
                    vetoed: *vetoed,
                    per_scorer: per_scorer.clone(),
                })
                .collect(),
        };
        (chosen, trace)
    }
}

fn capability(module: &str, payload: &str, needs_channel: bool, priority: i32) -> AttackCapability {
    AttackCapability {
        id: Uuid::new_v4(),
        service_match: "example".into(),
        module: module.into(),
        tool_type: "exploit".into(),
        default_payload: payload.into(),
        default_options: serde_json::json!({}),
        mitre: "T1210".into(),
        params_hint: String::new(),
        requires_creds: false,
        needs_channel,
        priority,
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn main() {
    let selector = MiniComposite::new(vec![Box::new(QuietVeto), Box::new(LowNoise)]);
    let ctx = SelectionContext::default();
    let candidates = [
        capability("noisy_reverse", "cmd/unix/reverse", true, 100),
        capability("quiet_local", "cmd/unix/interact", false, 100),
        capability("loud_meterpreter", "java/meterpreter/reverse_tcp", true, 120),
    ];

    let (chosen, trace) = selector.select(&candidates, &ctx);

    println!("athena-sdk example — custom CapabilitySelector `MiniComposite`\n");
    for cand in &trace.candidates {
        let mark = if cand.vetoed { "✗" } else { " " };
        println!("  {mark} {:18} total {:8.1}", cand.module, cand.total);
        for line in &cand.per_scorer {
            println!("        - {:12} {:+6.1}  {}", line.name, line.weight, line.reason);
        }
    }
    println!("\n→ chosen: {:?}", chosen.map(|c| c.module));
    println!("→ selection = 各 scorer 貢獻加總，veto 硬排除；第三方可自訂自己的選擇策略。");
}
