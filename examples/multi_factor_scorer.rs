// SPDX-License-Identifier: Apache-2.0
//! Minimal, self-contained example that depends ONLY on `athena-sdk`.
//!
//! Run: `cargo run --example multi_factor_scorer`
//!
//! Implements `CapabilityScorer` scoring on more than one orthogonal factor, and
//! shows the difference between a **weight** (additive, combinable) and a **veto**
//! (a hard exclusion — NOT a large negative weight). Factors:
//!   A. feasibility  → `veto` when a reverse channel is required but unavailable;
//!   B. trust risk   → penalty when low-trust facts back a loud payload;
//!   C. detection    → penalty scaled by the operator's stealth preference.

use athena_sdk::{
    payload_noise_cost, AttackCapability, CapabilityScorer, FactTrustSummary, NoiseClass, OpsecPref,
    ScoreContribution, SelectionContext,
};
use chrono::Utc;
use uuid::Uuid;

struct MultiFactorScorer;

impl MultiFactorScorer {
    const RISK_PENALTY: f64 = 10.0;
    const NOISE_PENALTY_PER_COST: f64 = 8.0;
    const MAX_WEIGHT: f64 = 90.0;
}

impl CapabilityScorer for MultiFactorScorer {
    fn name(&self) -> &str {
        "multi_factor"
    }

    fn score(&self, cap: &AttackCapability, ctx: &SelectionContext) -> ScoreContribution {
        // Factor A — hard feasibility veto (excluded before any summation).
        if cap.needs_channel && !ctx.channel_available {
            return ScoreContribution {
                weight: 0.0,
                veto: true,
                reason: "veto: needs a reverse channel but none is available".into(),
            };
        }

        let mut weight = 0.0;
        let mut parts: Vec<String> = Vec::new();
        let noise = payload_noise_cost(&cap.default_payload);
        let loud = matches!(noise, NoiseClass::Loud | NoiseClass::Blaring);

        // Factor B — trust risk: low-trust supporting facts + a loud payload.
        if ctx.fact_trust.fact_count > 0 && ctx.fact_trust.lowest_rank == Some(1) && loud {
            weight -= Self::RISK_PENALTY;
            parts.push(format!(
                "low-trust facts + {noise:?} payload → -{:.1} risk",
                Self::RISK_PENALTY
            ));
        }

        // Factor C — detection cost scaled by the operator's stealth preference.
        let stealth = ctx.opsec_pref.stealth_level.clamp(0.0, 1.0);
        if stealth > 0.0 {
            let pen = noise.cost() as f64 * Self::NOISE_PENALTY_PER_COST * stealth;
            weight -= pen;
            parts.push(format!(
                "{noise:?} (cost {}) × stealth {stealth:.2} → -{pen:.1}",
                noise.cost()
            ));
        }

        let weight = weight.clamp(-Self::MAX_WEIGHT, Self::MAX_WEIGHT);
        ScoreContribution {
            weight,
            veto: false,
            reason: if parts.is_empty() {
                "neutral (no active factors)".into()
            } else {
                parts.join("; ")
            },
        }
    }
}

fn capability(module: &str, payload: &str, needs_channel: bool) -> AttackCapability {
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
        priority: 100,
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn main() {
    let scorer = MultiFactorScorer;
    // Low-trust facts, no reverse channel, and a stealth-biased operator.
    let ctx = SelectionContext {
        channel_available: false,
        fact_trust: FactTrustSummary {
            fact_count: 2,
            lowest_rank: Some(1),
        },
        opsec_pref: OpsecPref { stealth_level: 0.8 },
        ..Default::default()
    };
    let caps = [
        capability("reverse_shell", "cmd/unix/reverse", true), // vetoed (needs channel)
        capability("loud_local", "windows/x64/meterpreter/bind_tcp", false), // risk + noise
        capability("quiet_local", "cmd/unix/interact", false), // small noise only
    ];

    println!("athena-sdk example — CapabilityScorer `{}`\n", scorer.name());
    for cap in &caps {
        let c = scorer.score(cap, &ctx);
        let mark = if c.veto { "✗ VETO" } else { "✓ keep" };
        println!("  {mark}  {:14} weight {:+7.1}  {}", cap.module, c.weight, c.reason);
    }
    println!("\n→ 多個正交因子組合：weight 可加總、veto 是硬排除（非大負值）。");
}
