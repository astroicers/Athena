// SPDX-License-Identifier: Apache-2.0
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use std::fmt;
use std::str::FromStr;
use crate::OperationId;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Fact {
    pub id: Uuid,
    pub op_id: OperationId,
    pub trait_name: FactTrait,
    pub value: FactValue,
    pub source: String,
    pub confidence: u8,
    pub collected_at: DateTime<Utc>,
    /// Trust class of where this fact came from (ADR-142a). Drives the DECIDE
    /// trust-gate (ADR-142b) and conflict-resolution on insert (higher rank wins).
    #[serde(default)]
    pub provenance: FactProvenance,
}

/// Where a fact came from — its trust class (ADR-142a). Orthogonal to `confidence`
/// (value-certainty): `provenance` is source-trust. `ShellOutput` is LOW trust because
/// it is controlled by the (possibly hostile) target; `Operator` is highest.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum FactProvenance {
    /// Active scan / enumeration we performed (nmap, scanner aux). Our observation.
    #[default]
    Scan,
    /// Result of an exploit landing (session opened, exploit uuid).
    ExploitResult,
    /// Output of a shell / session-exec — controlled by the target, LOW trust.
    ShellOutput,
    /// Derived from other facts.
    Derived,
    /// Injected by a human operator — highest trust.
    Operator,
}

impl FactProvenance {
    /// Trust rank for conflict-resolution and gating (higher = more trusted).
    /// NOTE: `ShellOutput` deliberately ranks as low as `Scan` is — it is target-controlled.
    pub fn rank(&self) -> u8 {
        match self {
            FactProvenance::Scan => 1,
            FactProvenance::ShellOutput => 1,
            FactProvenance::ExploitResult => 2,
            FactProvenance::Derived => 2,
            FactProvenance::Operator => 5,
        }
    }
}

impl fmt::Display for FactProvenance {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            FactProvenance::Scan => "Scan",
            FactProvenance::ExploitResult => "ExploitResult",
            FactProvenance::ShellOutput => "ShellOutput",
            FactProvenance::Derived => "Derived",
            FactProvenance::Operator => "Operator",
        };
        f.write_str(s)
    }
}

impl FromStr for FactProvenance {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "Scan" => Ok(FactProvenance::Scan),
            "ExploitResult" => Ok(FactProvenance::ExploitResult),
            "ShellOutput" => Ok(FactProvenance::ShellOutput),
            "Derived" => Ok(FactProvenance::Derived),
            "Operator" => Ok(FactProvenance::Operator),
            other => Err(format!("invalid FactProvenance: {other}")),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FactTrait(pub String);
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(untagged)]
pub enum FactValue {
    Text(String),
    Number(i64),
    Bool(bool),
}
