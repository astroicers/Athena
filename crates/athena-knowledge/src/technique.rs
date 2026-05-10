use crate::{TechniqueEntry, KnowledgeError, load_yaml_dir};
use std::path::PathBuf;

pub struct TechniqueLibrary {
    pub techniques: Vec<TechniqueEntry>,
}

impl TechniqueLibrary {
    pub fn load(data_dir: impl Into<PathBuf>) -> Result<Self, KnowledgeError> {
        let path = data_dir.into().join("techniques");
        let techniques = load_yaml_dir(&path)?;
        Ok(Self { techniques })
    }

    pub fn get(&self, id: &str) -> Option<&TechniqueEntry> {
        self.techniques.iter().find(|t| t.id == id)
    }

    pub fn by_category(&self, category: &str) -> Vec<&TechniqueEntry> {
        self.techniques.iter().filter(|t| t.category == category).collect()
    }
}
