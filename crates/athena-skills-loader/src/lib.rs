use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub content: String,
    pub tags: Vec<String>,
}

#[async_trait]
pub trait SkillsLoader: Send + Sync {
    async fn load_all(&self) -> Result<Vec<Skill>, AthenaError>;
    async fn get(&self, name: &str) -> Result<Option<Skill>, AthenaError>;
}

pub struct FileSystemSkillsLoader {
    pub base_path: PathBuf,
}

#[async_trait]
impl SkillsLoader for FileSystemSkillsLoader {
    async fn load_all(&self) -> Result<Vec<Skill>, AthenaError> {
        Ok(vec![])
    }
    async fn get(&self, _name: &str) -> Result<Option<Skill>, AthenaError> {
        Ok(None)
    }
}
