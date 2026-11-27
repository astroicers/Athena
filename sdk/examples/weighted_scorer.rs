// SPDX-License-Identifier: Apache-2.0
//! Minimal, self-contained example that depends ONLY on `athena-sdk`.
//!
//! Run: `cargo run --example weighted_scorer`
//!
//! Implements `CapabilityScorer` by combining several signals with tunable
//! weights into a single, bounded additive `weight`. Shows the canonical
//! "read signals → derive a numeric weight → clamp" shape: a scorer only ever
//! re-orders candidates of *equal* priority, so its contribution is bounded.

use athena_sdk::{
    payload_noise_cost, AttackCapability, CapabilityScorer, OpsecPref, ScoreContribution,
    SelectionContext,
};
use chrono::Utc;
use uuid::Uuid;

/// Combines a positive "specificity" signal with a negative "noise" signal,
/// each multiplied by a configurable weight, then clamps to a bounded range.
struct WeightedScorer {
    /// Points per extra matching `&&`-term (rewards a more specific match).
    w_specificity: f64,
    /// Points per unit of on-wire noise, scaled by operator stealth preference.
    w_noise: f64,
}

impl WeightedScorer {
    /// Bounded so any single scorer can only re-order equal-priority candidates.
    const MAX_WEIGHT: f64 = 90.0;

    /// Count the terms of the best-matching `||`-clause in `service_match`.
    /// Grammar (per the `AttackCapability::service_match` contract): OR-clauses are
    /// separated by `||`; AND-terms within a clause by `&&`; a `port:<N>` term
    /// matches an open-port string, any other term is a substring test on versions.
    fn matching_terms(cap: &AttackCapability, ctx: &SelectionContext) -> usize {
        cap.service_match
            .split("||")
            .filter_map(|clause| {
                let terms: Vec<&str> = clause
                    .split("&&")
                    .map(str::trim)
                    .filter(|t| !t.is_empty())
                    .collect();
                if terms.is_empty() {
                    return None;
                }
                let all = terms.iter().all(|term| {
                    if let Some(port) = term.strip_prefix("port:") {
                        let prefix = format!("{}/", port.trim());
                        ctx.ports.iter().any(|p| p.starts_with(&prefix))
                    } else {
                        ctx.versions.iter().any(|v| v.contains(*term))
                    }
                });
                if all {
                    Some(terms.len())
                } else {
                    None
                }
            })
            .max()
            .unwrap_or(0)
    }
}

impl CapabilityScorer for WeightedScorer {
    fn name(&self) -> &str {
        "weighted"
    }

    fn score(&self, cap: &AttackCapability, ctx: &SelectionContext) -> ScoreContribution {
        let terms = Self::matching_terms(cap, ctx);
        // Reward specificity beyond the first matching term.
        let specificity = terms.saturating_sub(1) as f64;
        let noise = payload_noise_cost(&cap.default_payload).cost() as f64;
        let stealth = ctx.opsec_pref.stealth_level.clamp(0.0, 1.0);

        let spec_pts = self.w_specificity * specificity;
        let noise_pts = self.w_noise * noise * stealth; // a penalty
        let weight = (spec_pts - noise_pts).clamp(-Self::MAX_WEIGHT, Self::MAX_WEIGHT);

        ScoreContribution {
            weight,
            veto: false,
            reason: format!(
                "specificity {terms} term(s) → +{spec_pts:.1}; noise {noise} × stealth {stealth:.2} → -{noise_pts:.1}; net {weight:+.1}"
            ),
        }
    }
}

fn capability(module: &str, service_match: &str, payload: &str) -> AttackCapability {
    AttackCapability {
        id: Uuid::new_v4(),
        service_match: service_match.into(),
        module: module.into(),
        tool_type: "exploit".into(),
        default_payload: payload.into(),
        default_options: serde_json::json!({}),
        mitre: "T1210".into(),
        params_hint: String::new(),
        requires_creds: false,
        needs_channel: payload.contains("reverse") || payload.contains("bind"),
        priority: 100,
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn main() {
    let scorer = WeightedScorer {
        w_specificity: 20.0,
        w_noise: 8.0,
    };
    let ctx = SelectionContext {
        versions: vec!["vsftpd 2.3.4".into(), "samba 3.0.20".into()],
        ports: vec!["21/tcp/ftp".into(), "445/tcp/microsoft-ds".into()],
        opsec_pref: OpsecPref { stealth_level: 0.5 },
        ..Default::default()
    };
    let caps = [
        capability("vsftpd_exploit", "vsftpd && 2.3.4", "cmd/unix/interact"),
        capability("samba_reverse", "samba && 3.0", "cmd/unix/reverse"),
        capability("generic_probe", "http", ""),
    ];

    println!("athena-sdk example — CapabilityScorer `{}`\n", scorer.name());
    for cap in &caps {
        let c = scorer.score(cap, &ctx);
        println!("  {:16} weight {:+7.1}  {}", cap.module, c.weight, c.reason);
    }
    println!("\n→ 多個信號加權加總成單一 bounded 分數；weight 只在同 priority 內重排候選。");
}
