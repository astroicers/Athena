use async_trait::async_trait;
use athena_types::AthenaError;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CveEntry {
    pub cve_id: String,
    pub cvss_score: f32,
    pub description: String,
    pub published: DateTime<Utc>,
}

#[async_trait]
pub trait VulnerabilityManager: Send + Sync {
    async fn lookup_cve(&self, cve_id: &str) -> Result<CveEntry, AthenaError>;
    async fn search_cves(&self, keyword: &str, limit: usize) -> Result<Vec<CveEntry>, AthenaError>;
}

// NVD 2.0 API client
const NVD_API_BASE: &str = "https://services.nvd.nist.gov/rest/json/cves/2.0";

pub struct NvdClient {
    client: Client,
    api_key: Option<String>,
}

impl NvdClient {
    pub fn new(api_key: Option<String>) -> Self {
        Self { client: Client::new(), api_key }
    }

    fn auth_header(&self) -> Option<(&'static str, String)> {
        self.api_key.as_ref().map(|k| ("apiKey", k.clone()))
    }

    fn parse_entry(vuln: &serde_json::Value) -> Option<CveEntry> {
        let cve = vuln.get("cve")?;
        let cve_id = cve.get("id")?.as_str()?.to_string();
        let description = cve.get("descriptions")?
            .as_array()?
            .iter()
            .find(|d| d.get("lang").and_then(|l| l.as_str()) == Some("en"))
            .and_then(|d| d.get("value"))
            .and_then(|v| v.as_str())
            .unwrap_or("No description")
            .to_string();

        let cvss_score = cve.get("metrics")
            .and_then(|m| m.get("cvssMetricV31").or(m.get("cvssMetricV30")).or(m.get("cvssMetricV2")))
            .and_then(|arr| arr.as_array())
            .and_then(|arr| arr.first())
            .and_then(|m| m.get("cvssData"))
            .and_then(|d| d.get("baseScore"))
            .and_then(|s| s.as_f64())
            .unwrap_or(0.0) as f32;

        let published = cve.get("published")
            .and_then(|v| v.as_str())
            .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
            .map(|d| d.with_timezone(&Utc))
            .unwrap_or_else(Utc::now);

        Some(CveEntry { cve_id, cvss_score, description, published })
    }
}

#[async_trait]
impl VulnerabilityManager for NvdClient {
    async fn lookup_cve(&self, cve_id: &str) -> Result<CveEntry, AthenaError> {
        let url = format!("{}?cveId={}", NVD_API_BASE, cve_id);
        let mut req = self.client.get(&url);
        if let Some((header, val)) = self.auth_header() {
            req = req.header(header, val);
        }

        let resp = req.send().await
            .map_err(|e| AthenaError::McpError(format!("NVD request failed: {e}")))?;

        if !resp.status().is_success() {
            let status = resp.status();
            return Err(AthenaError::McpError(format!("NVD API {status} for {cve_id}")));
        }

        let body: serde_json::Value = resp.json().await
            .map_err(|e| AthenaError::McpError(format!("NVD parse error: {e}")))?;

        body.get("vulnerabilities")
            .and_then(|arr| arr.as_array())
            .and_then(|arr| arr.first())
            .and_then(Self::parse_entry)
            .ok_or_else(|| AthenaError::OperationNotFound(format!("CVE not found: {cve_id}")))
    }

    async fn search_cves(&self, keyword: &str, limit: usize) -> Result<Vec<CveEntry>, AthenaError> {
        let url = format!("{}?keywordSearch={}&resultsPerPage={}", NVD_API_BASE, keyword, limit.min(100));
        let mut req = self.client.get(&url);
        if let Some((header, val)) = self.auth_header() {
            req = req.header(header, val);
        }

        let resp = req.send().await
            .map_err(|e| AthenaError::McpError(format!("NVD request failed: {e}")))?;

        if !resp.status().is_success() {
            return Ok(vec![]);
        }

        let body: serde_json::Value = resp.json().await
            .map_err(|e| AthenaError::McpError(format!("NVD parse error: {e}")))?;

        let entries = body.get("vulnerabilities")
            .and_then(|arr| arr.as_array())
            .map(|arr| arr.iter().filter_map(Self::parse_entry).collect())
            .unwrap_or_default();

        Ok(entries)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn parse_entry_extracts_fields() {
        let vuln = json!({
            "cve": {
                "id": "CVE-2021-44228",
                "published": "2021-12-10T10:15:09.143Z",
                "descriptions": [{ "lang": "en", "value": "Log4Shell RCE vulnerability" }],
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": { "baseScore": 10.0 }
                    }]
                }
            }
        });
        let entry = NvdClient::parse_entry(&vuln).unwrap();
        assert_eq!(entry.cve_id, "CVE-2021-44228");
        assert!((entry.cvss_score - 10.0).abs() < 0.01);
        assert!(entry.description.contains("Log4Shell"));
    }

    #[test]
    fn parse_entry_handles_missing_cvss() {
        let vuln = json!({
            "cve": {
                "id": "CVE-2023-99999",
                "published": "2023-01-01T00:00:00.000Z",
                "descriptions": [{ "lang": "en", "value": "Test CVE" }]
            }
        });
        let entry = NvdClient::parse_entry(&vuln).unwrap();
        assert_eq!(entry.cvss_score, 0.0);
    }

    #[test]
    fn parse_entry_returns_none_for_missing_id() {
        let vuln = json!({ "cve": {} });
        assert!(NvdClient::parse_entry(&vuln).is_none());
    }
}
