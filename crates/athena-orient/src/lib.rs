use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, OrientRecommendation, AthenaError};
use athena_llm_client::{LlmClient, LlmRequest};
use athena_pentest_kb::KnowledgeBase;
use athena_skills_loader::SkillsLoader;

#[async_trait]
pub trait OrientPhase: Send + Sync {
    async fn analyze(
        &self,
        op_id: &OperationId,
        observation_summary: &str,
        attack_graph_summary: &str,
    ) -> Result<OrientRecommendation, AthenaError>;
}

// 14 orient rules ported verbatim from v1 orient_engine.py system prompt
const ORIENT_SYSTEM_PROMPT: &str = r#"You are Athena's Orient Phase AI — a cyber operations analyst performing OODA loop orientation.

ORIENT RULES (apply all 14 in every analysis):
1. Enumerate all observed facts before drawing conclusions.
2. Map each fact to at least one MITRE ATT&CK technique ID (Txxxx.xxx format).
3. Prioritise techniques with confirmed evidence over speculation.
4. Assign risk_score ∈ [0.0, 1.0] where 1.0 = critical risk to operations.
5. Never recommend a technique whose prerequisites are unmet by current facts.
6. Consider lateral movement paths through observed open ports.
7. Weigh credential exposure facts as highest-priority attack surface.
8. Identify OS-specific technique applicability (Linux vs Windows variants).
9. Account for network segmentation facts before recommending techniques.
10. Order recommended_techniques by expected impact / feasibility ratio (highest first).
11. Never recommend more than 5 techniques per iteration.
12. Rationale must cite specific observed facts by trait_name and value.
13. If no facts are available, set risk_score=0.1 and recommend recon techniques only.
14. Output ONLY valid JSON matching the schema — no markdown, no preamble.

OUTPUT SCHEMA:
{
  "summary": "<1–2 sentence operational summary>",
  "recommended_techniques": ["Txxxx", ...],
  "risk_score": <float 0.0–1.0>,
  "rationale": "<fact-cited reasoning>"
}
"#;

pub struct ClaudeOrientEngine {
    llm: Arc<dyn LlmClient>,
    model: String,
    kb: Option<Arc<dyn KnowledgeBase>>,
    skills: Option<Arc<dyn SkillsLoader>>,
}

impl ClaudeOrientEngine {
    pub fn new(llm: Arc<dyn LlmClient>, model: impl Into<String>) -> Self {
        Self { llm, model: model.into(), kb: None, skills: None }
    }

    pub fn with_kb(mut self, kb: Arc<dyn KnowledgeBase>) -> Self {
        self.kb = Some(kb);
        self
    }

    pub fn with_skills(mut self, skills: Arc<dyn SkillsLoader>) -> Self {
        self.skills = Some(skills);
        self
    }
}

#[async_trait]
impl OrientPhase for ClaudeOrientEngine {
    async fn analyze(
        &self,
        op_id: &OperationId,
        observation_summary: &str,
        attack_graph_summary: &str,
    ) -> Result<OrientRecommendation, AthenaError> {
        // Fetch relevant KB snippets to ground the LLM recommendation
        let kb_context = if let Some(kb) = &self.kb {
            let entries = kb.search(observation_summary, 3).await.unwrap_or_default();
            if entries.is_empty() {
                String::new()
            } else {
                let snippets: Vec<String> = entries.iter().map(|e| {
                    format!("[{}] {}: {}", e.id, e.title, &e.content.chars().take(300).collect::<String>())
                }).collect();
                format!("\n\nRelevant KB entries:\n{}", snippets.join("\n---\n"))
            }
        } else {
            String::new()
        };

        // Inject relevant skill technique names into prompt context
        let skills_context = if let Some(sl) = &self.skills {
            let tmap = sl.technique_map().await.unwrap_or_default();
            if tmap.is_empty() {
                String::new()
            } else {
                let names: Vec<&str> = tmap.keys().take(5).map(String::as_str).collect();
                format!("\n\nAvailable skills: {}", names.join(", "))
            }
        } else {
            String::new()
        };

        let user_msg = format!(
            "Operation ID: {op_id}\n\nObservation summary:\n{observation_summary}\n\nAttack graph:\n{attack_graph_summary}{kb_context}{skills_context}\n\nApply all 14 orient rules. Return JSON only."
        );

        let req = LlmRequest::new(&self.model, ORIENT_SYSTEM_PROMPT, user_msg);
        let resp = self.llm.complete(req).await?;

        serde_json::from_str::<OrientRecommendation>(&resp.content)
            .map_err(|e| AthenaError::LlmError(format!(
                "orient JSON parse failed: {e}\nraw: {}", resp.content
            )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_llm_client::MockLlmClient;
    use athena_pentest_kb::{KbEntry, KbCategory};

    fn mock_orient_json() -> &'static str {
        r#"{"summary":"Host exposes SSH and HTTP.","recommended_techniques":["T1046","T1078","T1059.004"],"risk_score":0.65,"rationale":"open_port:22 indicates SSH; T1046 for network scanning."}"#
    }

    #[tokio::test]
    async fn analyze_parses_llm_json() {
        let llm = Arc::new(MockLlmClient::with_response(mock_orient_json()));
        let engine = ClaudeOrientEngine::new(llm, "mock");
        let op_id = OperationId::new();

        let rec = engine.analyze(&op_id, "2 open ports: 22, 80", "").await.unwrap();
        assert_eq!(rec.recommended_techniques, vec!["T1046", "T1078", "T1059.004"]);
        assert!((rec.risk_score - 0.65).abs() < 0.001);
        assert!(!rec.summary.is_empty());
    }

    #[tokio::test]
    async fn analyze_returns_err_on_invalid_json() {
        let llm = Arc::new(MockLlmClient::with_response("not json"));
        let engine = ClaudeOrientEngine::new(llm, "mock");
        let op_id = OperationId::new();

        let result = engine.analyze(&op_id, "obs", "graph").await;
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("orient JSON parse failed"));
    }

    #[test]
    fn system_prompt_contains_all_14_rules() {
        for i in 1..=14 {
            assert!(
                ORIENT_SYSTEM_PROMPT.contains(&format!("{i}. ")),
                "Rule {i} missing from orient system prompt"
            );
        }
    }

    struct MockKb;
    #[async_trait]
    impl KnowledgeBase for MockKb {
        async fn search(&self, _q: &str, _limit: usize) -> Result<Vec<KbEntry>, AthenaError> {
            Ok(vec![KbEntry {
                id: "priv-001".into(),
                title: "Linux SUID Escalation".into(),
                category: KbCategory::PrivilegeEscalation,
                tags: vec!["linux".into()],
                platform: vec!["linux".into()],
                content: "Find SUID binaries with find / -perm -4000.".into(),
                commands: vec!["find / -perm -4000 2>/dev/null".into()],
                references: vec![],
            }])
        }
        async fn get(&self, _id: &str) -> Result<Option<KbEntry>, AthenaError> { Ok(None) }
        async fn list_by_category(&self, _c: &KbCategory) -> Result<Vec<KbEntry>, AthenaError> { Ok(vec![]) }
    }

    #[tokio::test]
    async fn analyze_with_kb_injects_context() {
        let llm = Arc::new(MockLlmClient::with_response(mock_orient_json()));
        let engine = ClaudeOrientEngine::new(llm, "mock")
            .with_kb(Arc::new(MockKb));
        let op_id = OperationId::new();
        // Should still parse correctly with KB context injected
        let rec = engine.analyze(&op_id, "open_port:22", "").await.unwrap();
        assert!(!rec.recommended_techniques.is_empty());
    }
}
