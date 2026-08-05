// Mirrors the "可跑範例" scorer from docs/extending.md. Kept in lock-step with the
// doc so CI proves the teaching snippet compiles against the public SDK contract.
use athena_sdk::{AttackCapability, CapabilityScorer, ScoreContribution, SelectionContext};

/// 偏好「安靜」的能力：否決任何需要吵雜 reverse 回連通道的手法。
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

fn main() {
    // Boxing as the trait object proves the impl satisfies the object-safe contract
    // the selection layer consumes.
    let scorer: Box<dyn CapabilityScorer> = Box::new(QuietPreference);
    println!(
        "scorer-check: `{}` compiles against the public athena-sdk contract",
        scorer.name()
    );
}
