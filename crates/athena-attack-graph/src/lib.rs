use async_trait::async_trait;
use athena_types::{OperationId, AthenaError};
use athena_knowledge::{TechniqueEntry, RiskLevel};
use serde::{Deserialize, Serialize};
use std::collections::{BinaryHeap, HashMap, HashSet};
use std::cmp::Reverse;

// ── domain types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttackPath {
    pub nodes: Vec<AttackNode>,
    pub total_risk: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttackNode {
    pub technique_id: String,
    pub prerequisite: Option<String>,
    pub risk: f32,
}

// ── trait ─────────────────────────────────────────────────────────────────────

#[async_trait]
pub trait AttackGraphEngine: Send + Sync {
    async fn compute_paths(
        &self,
        op_id: &OperationId,
        entry_points: Vec<String>,
    ) -> Result<Vec<AttackPath>, AthenaError>;

    async fn to_summary(&self, paths: &[AttackPath]) -> String;
}

// ── risk scoring ──────────────────────────────────────────────────────────────

fn risk_weight(level: &RiskLevel) -> f32 {
    match level {
        RiskLevel::Low      => 1.0,
        RiskLevel::Medium   => 2.0,
        RiskLevel::High     => 4.0,
        RiskLevel::Critical => 8.0,
    }
}

// ── Dijkstra-based implementation ─────────────────────────────────────────────

/// Builds an attack graph from a `Vec<TechniqueEntry>` and finds the shortest
/// (lowest cumulative risk) paths from given entry points.
///
/// Edges: technique A → technique B when B lists A in its `prerequisites`.
pub struct DijkstraAttackGraph {
    techniques: Vec<TechniqueEntry>,
}

impl DijkstraAttackGraph {
    pub fn new(techniques: Vec<TechniqueEntry>) -> Self {
        Self { techniques }
    }

    fn by_id(&self, id: &str) -> Option<&TechniqueEntry> {
        self.techniques.iter().find(|t| t.id == id)
    }

    /// Returns adjacency list: id → Vec<child_id>
    fn adjacency(&self) -> HashMap<String, Vec<String>> {
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();
        for t in &self.techniques {
            adj.entry(t.id.clone()).or_default();
            for prereq in &t.prerequisites {
                adj.entry(prereq.clone()).or_default().push(t.id.clone());
            }
        }
        adj
    }

    fn dijkstra(&self, start: &str) -> HashMap<String, (f32, Option<String>)> {
        let adj = self.adjacency();
        // dist[id] = (cumulative_risk, prev_id)
        let mut dist: HashMap<String, (f32, Option<String>)> = HashMap::new();
        // min-heap: (cost * 1000 as u64, id)
        let mut heap: BinaryHeap<Reverse<(u64, String)>> = BinaryHeap::new();

        let start_risk = self.by_id(start)
            .map(|t| risk_weight(&t.risk_level))
            .unwrap_or(1.0);

        dist.insert(start.to_string(), (start_risk, None));
        heap.push(Reverse(((start_risk * 1000.0) as u64, start.to_string())));

        while let Some(Reverse((cost_k, id))) = heap.pop() {
            let cost = cost_k as f32 / 1000.0;
            if let Some(&(d, _)) = dist.get(&id) {
                if cost > d + f32::EPSILON {
                    continue;
                }
            }
            let children = adj.get(&id).cloned().unwrap_or_default();
            for child in children {
                let child_risk = self.by_id(&child)
                    .map(|t| risk_weight(&t.risk_level))
                    .unwrap_or(1.0);
                let new_cost = cost + child_risk;
                let better = dist.get(&child)
                    .map(|&(d, _)| new_cost < d - f32::EPSILON)
                    .unwrap_or(true);
                if better {
                    dist.insert(child.clone(), (new_cost, Some(id.clone())));
                    heap.push(Reverse(((new_cost * 1000.0) as u64, child.clone())));
                }
            }
        }
        dist
    }

    fn reconstruct_path(&self, dist: &HashMap<String, (f32, Option<String>)>, target: &str) -> AttackPath {
        let mut nodes = Vec::new();
        let mut cur = target.to_string();
        loop {
            let (_risk, prev) = match dist.get(&cur) {
                Some(v) => v.clone(),
                None => break,
            };
            let node_risk = self.by_id(&cur)
                .map(|t| risk_weight(&t.risk_level))
                .unwrap_or(1.0);
            nodes.push(AttackNode { technique_id: cur.clone(), prerequisite: prev.clone(), risk: node_risk });
            match prev {
                Some(p) => cur = p,
                None => break,
            }
        }
        nodes.reverse();
        let total_risk = dist.get(target).map(|&(r, _)| r).unwrap_or(0.0);
        AttackPath { nodes, total_risk }
    }
}

#[async_trait]
impl AttackGraphEngine for DijkstraAttackGraph {
    async fn compute_paths(
        &self,
        _op_id: &OperationId,
        entry_points: Vec<String>,
    ) -> Result<Vec<AttackPath>, AthenaError> {
        let mut paths = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();

        for entry in &entry_points {
            let dist = self.dijkstra(entry);
            // Emit a path for every reachable node not yet covered
            for (target, _) in &dist {
                if !seen.contains(target) {
                    seen.insert(target.clone());
                    let path = self.reconstruct_path(&dist, target);
                    if !path.nodes.is_empty() {
                        paths.push(path);
                    }
                }
            }
        }

        // Sort by total_risk ascending
        paths.sort_by(|a, b| a.total_risk.partial_cmp(&b.total_risk).unwrap_or(std::cmp::Ordering::Equal));
        Ok(paths)
    }

    async fn to_summary(&self, paths: &[AttackPath]) -> String {
        if paths.is_empty() {
            return "No attack paths identified.".into();
        }
        let mut lines = vec![format!("Attack graph: {} path(s) identified", paths.len())];
        for (i, path) in paths.iter().take(5).enumerate() {
            let chain: Vec<&str> = path.nodes.iter().map(|n| n.technique_id.as_str()).collect();
            lines.push(format!("  Path {}: {} (risk={:.1})", i + 1, chain.join(" → "), path.total_risk));
        }
        lines.join("\n")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_technique(id: &str, risk: RiskLevel, prereqs: Vec<&str>) -> TechniqueEntry {
        TechniqueEntry {
            id: id.into(),
            name: id.into(),
            description: String::new(),
            category: "test".into(),
            mcp_tool: None,
            parameters: vec![],
            prerequisites: prereqs.into_iter().map(String::from).collect(),
            risk_level: risk,
        }
    }

    fn graph() -> DijkstraAttackGraph {
        DijkstraAttackGraph::new(vec![
            make_technique("T1595", RiskLevel::Low, vec![]),
            make_technique("T1046", RiskLevel::Low, vec!["T1595"]),
            make_technique("T1190", RiskLevel::Medium, vec!["T1046"]),
            make_technique("T1548", RiskLevel::High, vec!["T1190"]),
        ])
    }

    #[tokio::test]
    async fn paths_computed_from_entry() {
        let g = graph();
        let op_id = OperationId::new();
        let paths = g.compute_paths(&op_id, vec!["T1595".into()]).await.unwrap();
        assert!(!paths.is_empty());
        // T1595 itself should appear
        assert!(paths.iter().any(|p| p.nodes[0].technique_id == "T1595"));
    }

    #[tokio::test]
    async fn path_follows_prerequisites() {
        let g = graph();
        let op_id = OperationId::new();
        let paths = g.compute_paths(&op_id, vec!["T1595".into()]).await.unwrap();
        // Find the path ending at T1548
        let t1548_path = paths.iter().find(|p| {
            p.nodes.last().map(|n| n.technique_id.as_str()) == Some("T1548")
        });
        assert!(t1548_path.is_some());
        let chain: Vec<&str> = t1548_path.unwrap().nodes.iter().map(|n| n.technique_id.as_str()).collect();
        assert_eq!(chain, vec!["T1595", "T1046", "T1190", "T1548"]);
    }

    #[tokio::test]
    async fn total_risk_is_cumulative() {
        let g = graph();
        let op_id = OperationId::new();
        let paths = g.compute_paths(&op_id, vec!["T1595".into()]).await.unwrap();
        // T1595(1) + T1046(1) + T1190(2) + T1548(4) = 8.0
        let t1548_path = paths.iter().find(|p| {
            p.nodes.last().map(|n| n.technique_id.as_str()) == Some("T1548")
        }).unwrap();
        assert!((t1548_path.total_risk - 8.0).abs() < 0.01);
    }

    #[tokio::test]
    async fn empty_entry_points_returns_empty() {
        let g = graph();
        let op_id = OperationId::new();
        let paths = g.compute_paths(&op_id, vec![]).await.unwrap();
        assert!(paths.is_empty());
    }

    #[tokio::test]
    async fn summary_formats_paths() {
        let g = graph();
        let op_id = OperationId::new();
        let paths = g.compute_paths(&op_id, vec!["T1595".into()]).await.unwrap();
        let summary = g.to_summary(&paths).await;
        assert!(summary.contains("Path 1:"));
        assert!(summary.contains("T1595"));
    }

    #[tokio::test]
    async fn empty_summary() {
        let g = graph();
        let summary = g.to_summary(&[]).await;
        assert!(summary.contains("No attack paths"));
    }
}
