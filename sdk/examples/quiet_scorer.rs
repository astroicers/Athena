// SPDX-License-Identifier: Apache-2.0
//! Minimal, self-contained example — depends ONLY on `athena-sdk`.
//!
//! Run:  `cargo run --example quiet_scorer`
//!
//! Implements the `CapabilityScorer` contract and shows it vetoing a "noisy"
//! (reverse-channel) capability in favor of a quiet one — the kind of pluggable
//! decision module a third party ships against the SDK.

use athena_sdk::{AttackCapability, CapabilityScorer, ScoreContribution, SelectionContext};
use chrono::Utc;
use uuid::Uuid;

/// Prefers "quiet" capabilities: vetoes anything needing a noisy reverse callback channel.
struct QuietPreference;

impl CapabilityScorer for QuietPreference {
    fn name(&self) -> &str {
        "quiet_preference"
    }

    fn score(&self, cap: &AttackCapability, _ctx: &SelectionContext) -> ScoreContribution {
        ScoreContribution {
            weight: 0.0,
            veto: cap.needs_channel,
            reason: if cap.needs_channel {
                "vetoed: needs a noisy reverse channel".into()
            } else {
                "kept: quiet (no reverse channel)".into()
            },
        }
    }
}

fn capability(module: &str, needs_channel: bool) -> AttackCapability {
    AttackCapability {
        id: Uuid::new_v4(),
        service_match: "vsftpd && 2.3.4".into(),
        module: module.into(),
        tool_type: "exploit".into(),
        default_payload: String::new(),
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
    let scorer = QuietPreference;
    let ctx = SelectionContext::default();
    let caps = [
        capability("noisy_reverse_mod", true),
        capability("quiet_bind_mod", false),
    ];

    println!("athena-sdk example — CapabilityScorer `{}`\n", scorer.name());
    for cap in &caps {
        let c = scorer.score(cap, &ctx);
        let mark = if c.veto { "✗ VETO" } else { "✓ keep" };
        println!("  {mark}  {:18}  {}", cap.module, c.reason);
    }
    println!("\n→ 外部模組只依賴 athena-sdk（零 athena-*）就能決定「打哪個」。");
}
