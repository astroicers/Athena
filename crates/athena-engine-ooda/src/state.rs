use serde::{Deserialize, Serialize};
use athena_types::{OperationId, OodaIterationId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OodaState {
    Idle,
    Observing,
    Orienting,
    Deciding,
    Acting,
    Completed,
    Aborted,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OodaContext {
    pub op_id: OperationId,
    pub iter_id: OodaIterationId,
    pub state: OodaState,
    pub iteration_count: u32,
}
