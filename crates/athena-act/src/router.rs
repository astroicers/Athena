use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, Decision, OodaIterationId, ExecutionOutcome, ExecutionResult, AthenaError};
use athena_exec_ssh::ExecutionEngine;
use athena_mcp_client::{McpClient, HttpMcpClient};
use athena_mcp_fact_extractor::FactExtractor;
use crate::ActPhase;

pub struct ActRouter {
    ssh: Option<Arc<dyn ExecutionEngine>>,
    mcp: Option<Arc<dyn McpClient>>,
    extractor: Arc<dyn FactExtractor>,
}

impl ActRouter {
    pub fn new(
        ssh: Option<Arc<dyn ExecutionEngine>>,
        mcp: Option<Arc<dyn McpClient>>,
        extractor: Arc<dyn FactExtractor>,
    ) -> Self {
        Self { ssh, mcp, extractor }
    }

    // Route technique to best available engine
    fn route_technique(&self, technique_id: &str) -> EngineChoice {
        // If there's an MCP mapping, prefer MCP for network-level recon techniques
        if self.mcp.is_some() && HttpMcpClient::technique_to_tool(technique_id).is_some() {
            return EngineChoice::Mcp;
        }
        if self.ssh.is_some() {
            return EngineChoice::Ssh;
        }
        EngineChoice::None
    }
}

enum EngineChoice {
    Mcp,
    Ssh,
    None,
}

#[async_trait]
impl ActPhase for ActRouter {
    async fn execute(
        &self,
        op_id: &OperationId,
        decision: &Decision,
        _iter_id: &OodaIterationId,
    ) -> Result<ExecutionOutcome, AthenaError> {
        if !decision.approved {
            return Ok(ExecutionOutcome { results: vec![], facts_collected: 0 });
        }

        let mut results: Vec<ExecutionResult> = vec![];
        let mut total_facts = 0usize;

        let dummy_target = athena_types::Target {
            id: athena_types::TargetId::new(),
            hostname: None,
            ip: None,
            os: None,
            tags: vec![],
        };
        let dummy_params = athena_types::TechniqueParams {
            technique_id: String::new(),
            params: serde_json::json!({}),
        };

        for technique in &decision.techniques {
            match self.route_technique(technique) {
                EngineChoice::Mcp => {
                    let mcp = self.mcp.as_ref().unwrap();
                    let tool = HttpMcpClient::technique_to_tool(technique).unwrap();
                    match mcp.call(tool, serde_json::json!({ "op_id": op_id.to_string() })).await {
                        Ok(mcp_result) => {
                            let facts = self.extractor.extract(&mcp_result, op_id).await?;
                            let new_fact_ids: Vec<String> = facts.iter()
                                .map(|f| f.trait_name.0.clone())
                                .collect();
                            total_facts += facts.len();
                            results.push(ExecutionResult {
                                technique_id: technique.clone(),
                                success: true,
                                output: mcp_result.output.to_string(),
                                new_facts: new_fact_ids,
                            });
                        }
                        Err(e) => {
                            tracing::warn!(technique = %technique, error = %e, "MCP execution failed");
                            results.push(ExecutionResult {
                                technique_id: technique.clone(),
                                success: false,
                                output: e.to_string(),
                                new_facts: vec![],
                            });
                        }
                    }
                }
                EngineChoice::Ssh => {
                    let ssh = self.ssh.as_ref().unwrap();
                    match ssh.execute(technique, &dummy_target, &dummy_params).await {
                        Ok(r) => results.push(r),
                        Err(e) => {
                            tracing::warn!(technique = %technique, error = %e, "SSH execution failed");
                            results.push(ExecutionResult {
                                technique_id: technique.clone(),
                                success: false,
                                output: e.to_string(),
                                new_facts: vec![],
                            });
                        }
                    }
                }
                EngineChoice::None => {
                    results.push(ExecutionResult {
                        technique_id: technique.clone(),
                        success: false,
                        output: format!("No engine available for technique {technique}"),
                        new_facts: vec![],
                    });
                }
            }
        }

        Ok(ExecutionOutcome { results, facts_collected: total_facts })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_mcp_client::McpToolResult;
    use athena_mcp_fact_extractor::McpFactExtractor;
    use serde_json::json;

    struct MockMcp;
    #[async_trait]
    impl McpClient for MockMcp {
        async fn call(&self, tool: &str, _params: serde_json::Value) -> Result<McpToolResult, AthenaError> {
            Ok(McpToolResult {
                tool: tool.into(),
                output: json!({ "open_ports": ["22", "80"] }),
                success: true,
                error: None,
            })
        }
        async fn health_check(&self, _tool: &str) -> bool { true }
        fn available_tools(&self) -> Vec<String> { vec!["nmap".into()] }
    }

    fn make_decision(techniques: &[&str]) -> Decision {
        Decision {
            approved: true,
            techniques: techniques.iter().map(|s| s.to_string()).collect(),
            reason: "test".into(),
            risk_accepted: 0.3,
        }
    }

    #[tokio::test]
    async fn routes_t1046_to_mcp() {
        let router = ActRouter::new(
            None,
            Some(Arc::new(MockMcp)),
            Arc::new(McpFactExtractor::new()),
        );
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let outcome = router.execute(&op_id, &make_decision(&["T1046"]), &iter_id).await.unwrap();
        assert_eq!(outcome.results.len(), 1);
        assert!(outcome.results[0].success);
        assert_eq!(outcome.facts_collected, 2); // 2 open ports extracted
    }

    #[tokio::test]
    async fn unapproved_decision_returns_empty() {
        let router = ActRouter::new(None, None, Arc::new(McpFactExtractor::new()));
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let decision = Decision {
            approved: false,
            techniques: vec!["T1046".into()],
            reason: "blocked".into(),
            risk_accepted: 0.9,
        };
        let outcome = router.execute(&op_id, &decision, &iter_id).await.unwrap();
        assert!(outcome.results.is_empty());
        assert_eq!(outcome.facts_collected, 0);
    }

    #[tokio::test]
    async fn no_engine_returns_failure_result() {
        let router = ActRouter::new(None, None, Arc::new(McpFactExtractor::new()));
        let op_id = OperationId::new();
        let iter_id = OodaIterationId::new();
        let outcome = router.execute(&op_id, &make_decision(&["T9999"]), &iter_id).await.unwrap();
        assert_eq!(outcome.results.len(), 1);
        assert!(!outcome.results[0].success);
        assert!(outcome.results[0].output.contains("No engine available"));
    }
}
