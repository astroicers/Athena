use async_trait::async_trait;
use std::sync::Arc;
use athena_types::{OperationId, AthenaError, FactValue};
use athena_facts::FactRepository;
use serde::{Deserialize, Serialize};
use chrono::Utc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PentestReport {
    pub op_id: String,
    pub title: String,
    pub executive_summary: String,
    pub findings: Vec<Finding>,
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub title: String,
    pub severity: Severity,
    pub description: String,
    pub remediation: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
    Informational,
}

impl std::fmt::Display for Severity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Severity::Critical => "CRITICAL",
            Severity::High => "HIGH",
            Severity::Medium => "MEDIUM",
            Severity::Low => "LOW",
            Severity::Informational => "INFO",
        };
        write!(f, "{s}")
    }
}

#[async_trait]
pub trait ReportGenerator: Send + Sync {
    async fn generate(&self, op_id: &OperationId) -> Result<PentestReport, AthenaError>;
    async fn to_markdown(&self, report: &PentestReport) -> String;
    async fn to_json(&self, report: &PentestReport) -> serde_json::Value;
}

pub struct FactReportGenerator {
    fact_repo: Arc<dyn FactRepository>,
}

impl FactReportGenerator {
    pub fn new(fact_repo: Arc<dyn FactRepository>) -> Self {
        Self { fact_repo }
    }

    /// Returns None for metadata/control facts that should not appear as findings.
    fn severity_for_trait(trait_name: &str) -> Option<Severity> {
        let s = if trait_name.starts_with("valid_credential") || trait_name.starts_with("access.") {
            Severity::Critical
        } else if trait_name.starts_with("web.vuln") || trait_name.starts_with("vulnerability") {
            Severity::High
        } else if trait_name.starts_with("service.open_port") || trait_name == "open_port" {
            Severity::Medium
        } else if trait_name == "local_user" || trait_name.starts_with("user.") {
            Severity::Medium
        } else if trait_name.starts_with("network.host") || trait_name == "network_segment" {
            Severity::Low
        } else if trait_name == "host.os" || trait_name == "os" || trait_name == "hostname" {
            Severity::Informational
        } else if trait_name == "target_ip" || trait_name == "target_hostname"
            || trait_name == "human_approved" || trait_name == "operator_override"
        {
            // Metadata facts — not security findings
            return None;
        } else {
            Severity::Informational
        };
        Some(s)
    }

    fn remediation_for_trait(trait_name: &str) -> &'static str {
        if trait_name.starts_with("valid_credential") || trait_name.starts_with("access.") {
            "Rotate credentials immediately. Implement MFA and enforce strong password policy."
        } else if trait_name.starts_with("web.vuln") || trait_name.starts_with("vulnerability") {
            "Apply vendor patches immediately. Implement compensating controls if patching is not immediately possible."
        } else if trait_name.starts_with("service.open_port") || trait_name == "open_port" {
            "Restrict unnecessary port exposure via firewall rules. Apply principle of least privilege."
        } else if trait_name == "local_user" || trait_name.starts_with("user.") {
            "Review local accounts. Disable or remove unnecessary accounts and enforce least privilege."
        } else if trait_name.starts_with("network") {
            "Implement network segmentation. Restrict inter-segment communication via firewall ACLs."
        } else {
            "Review and remediate according to security policy."
        }
    }
}

#[async_trait]
impl ReportGenerator for FactReportGenerator {
    async fn generate(&self, op_id: &OperationId) -> Result<PentestReport, AthenaError> {
        let facts = self.fact_repo.list(op_id).await?;
        let mut findings = Vec::new();
        let mut finding_idx = 1usize;

        // Group facts by trait for deduplication
        let mut by_trait: std::collections::BTreeMap<String, Vec<String>> = Default::default();
        for fact in &facts {
            let val = match &fact.value {
                FactValue::Text(s) => s.clone(),
                FactValue::Number(n) => n.to_string(),
                FactValue::Bool(b) => b.to_string(),
            };
            by_trait.entry(fact.trait_name.0.clone()).or_default().push(val);
        }

        for (trait_name, values) in &by_trait {
            let Some(severity) = Self::severity_for_trait(trait_name) else {
                continue; // skip metadata / control facts
            };
            let remediation = Self::remediation_for_trait(trait_name);
            // Truncate long value lists for readability
            let display_values = if values.len() > 5 {
                format!("{} (and {} more)", values[..5].join(", "), values.len() - 5)
            } else {
                values.join(", ")
            };
            findings.push(Finding {
                id: format!("FIND-{finding_idx:03}"),
                title: format!("{}: {}",
                    trait_name.replace(['.', '_'], " ").to_uppercase(),
                    &display_values[..display_values.len().min(80)]),
                severity,
                description: format!("Discovered {} '{}' instance(s): {}",
                    values.len(), trait_name, values.join(", ")),
                remediation: remediation.into(),
            });
            finding_idx += 1;
        }

        // Sort by severity
        findings.sort_by_key(|f| match f.severity {
            Severity::Critical => 0,
            Severity::High => 1,
            Severity::Medium => 2,
            Severity::Low => 3,
            Severity::Informational => 4,
        });

        let critical_count = findings.iter().filter(|f| f.severity == Severity::Critical).count();
        let high_count = findings.iter().filter(|f| f.severity == Severity::High).count();

        let executive_summary = format!(
            "This assessment identified {} finding(s) across {} unique observation types. \
            {} critical and {} high severity findings require immediate attention.",
            findings.len(), by_trait.len(), critical_count, high_count
        );

        Ok(PentestReport {
            op_id: op_id.to_string(),
            title: format!("Penetration Test Report — Operation {op_id}"),
            executive_summary,
            findings,
            generated_at: Utc::now(),
        })
    }

    async fn to_markdown(&self, report: &PentestReport) -> String {
        let mut lines = vec![
            format!("# {}", report.title),
            format!("Generated: {}\n", report.generated_at.format("%Y-%m-%d %H:%M UTC")),
            "## Executive Summary\n".into(),
            report.executive_summary.clone(),
            "\n## Findings\n".into(),
        ];
        for finding in &report.findings {
            lines.push(format!("### {} — {}", finding.id, finding.title));
            lines.push(format!("**Severity:** {}", finding.severity));
            lines.push(format!("**Description:** {}", finding.description));
            lines.push(format!("**Remediation:** {}\n", finding.remediation));
        }
        lines.join("\n")
    }

    async fn to_json(&self, report: &PentestReport) -> serde_json::Value {
        serde_json::to_value(report).unwrap_or(serde_json::json!({}))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use athena_facts::InMemoryFactRepository;
    use athena_types::{Fact, FactTrait};
    use uuid::Uuid;
    use chrono::Utc;

    async fn repo_with_facts(op_id: &OperationId) -> Arc<InMemoryFactRepository> {
        let repo = Arc::new(InMemoryFactRepository::new());
        for (trait_name, value) in [
            ("valid_credential", "admin:admin123"),
            ("open_port", "22"),
            ("vulnerability", "CVE-2021-44228"),
        ] {
            repo.insert(Fact {
                id: Uuid::new_v4(),
                op_id: op_id.clone(),
                trait_name: FactTrait(trait_name.into()),
                value: FactValue::Text(value.into()),
                source: "test".into(),
                confidence: 90,
                collected_at: Utc::now(),
            }).await.unwrap();
        }
        repo
    }

    #[tokio::test]
    async fn report_has_findings_sorted_by_severity() {
        let op_id = OperationId::new();
        let repo = repo_with_facts(&op_id).await;
        let generator = FactReportGenerator::new(repo);
        let report = generator.generate(&op_id).await.unwrap();
        assert_eq!(report.findings[0].severity, Severity::Critical);
        assert!(report.executive_summary.contains("1 critical"));
    }

    #[tokio::test]
    async fn to_markdown_contains_finding_ids() {
        let op_id = OperationId::new();
        let repo = repo_with_facts(&op_id).await;
        let generator = FactReportGenerator::new(repo);
        let report = generator.generate(&op_id).await.unwrap();
        let md = generator.to_markdown(&report).await;
        assert!(md.contains("FIND-001"));
        assert!(md.contains("Executive Summary"));
    }

    #[tokio::test]
    async fn to_json_is_valid() {
        let op_id = OperationId::new();
        let repo = Arc::new(InMemoryFactRepository::new());
        let generator = FactReportGenerator::new(repo);
        let report = generator.generate(&op_id).await.unwrap();
        let json = generator.to_json(&report).await;
        assert!(json.get("findings").is_some());
        assert_eq!(json["findings"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn empty_operation_report() {
        let op_id = OperationId::new();
        let repo = Arc::new(InMemoryFactRepository::new());
        let generator = FactReportGenerator::new(repo);
        let report = generator.generate(&op_id).await.unwrap();
        assert!(report.findings.is_empty());
        assert!(report.executive_summary.contains("0 finding"));
    }
}
