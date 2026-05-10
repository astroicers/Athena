use async_trait::async_trait;
use athena_types::AthenaError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tracing::warn;

// ── domain types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub content: String,
    pub tags: Vec<String>,
    pub techniques: Vec<String>,
}

/// Frontmatter parsed from the `---` YAML block at the top of a skill file.
#[derive(Debug, Deserialize, Default)]
struct SkillFrontmatter {
    #[serde(default)]
    name: String,
    #[serde(default)]
    description: String,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    techniques: Vec<String>,
}

// ── trait ─────────────────────────────────────────────────────────────────────

#[async_trait]
pub trait SkillsLoader: Send + Sync {
    async fn load_all(&self) -> Result<Vec<Skill>, AthenaError>;
    async fn get(&self, name: &str) -> Result<Option<Skill>, AthenaError>;
    /// Returns a name→content map for injecting into LLM prompts.
    async fn technique_map(&self) -> Result<HashMap<String, String>, AthenaError>;
}

// ── filesystem implementation ─────────────────────────────────────────────────

pub struct FileSystemSkillsLoader {
    pub base_path: PathBuf,
}

impl FileSystemSkillsLoader {
    pub fn new(base_path: impl Into<PathBuf>) -> Self {
        Self { base_path: base_path.into() }
    }
}

fn parse_skill_file(path: &Path) -> Option<Skill> {
    let raw = std::fs::read_to_string(path).ok()?;

    // Extract YAML frontmatter between --- delimiters
    let (frontmatter_str, body) = if raw.starts_with("---") {
        let rest = &raw[3..];
        if let Some(end) = rest.find("\n---") {
            let fm = &rest[..end];
            let content = rest[end + 4..].trim_start_matches('\n');
            (fm.to_string(), content.to_string())
        } else {
            (String::new(), raw.clone())
        }
    } else {
        (String::new(), raw.clone())
    };

    let fm: SkillFrontmatter = if frontmatter_str.is_empty() {
        SkillFrontmatter::default()
    } else {
        serde_yaml::from_str(&frontmatter_str).unwrap_or_default()
    };

    // Use filename stem as fallback name
    let name = if fm.name.is_empty() {
        path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string()
    } else {
        fm.name
    };

    Some(Skill {
        name,
        description: fm.description,
        content: body,
        tags: fm.tags,
        techniques: fm.techniques,
    })
}

#[async_trait]
impl SkillsLoader for FileSystemSkillsLoader {
    async fn load_all(&self) -> Result<Vec<Skill>, AthenaError> {
        let path = self.base_path.clone();
        tokio::task::spawn_blocking(move || {
            let mut skills = Vec::new();
            let entries = std::fs::read_dir(&path)
                .map_err(|e| AthenaError::Internal(format!("read_dir {path:?}: {e}")))?;

            for entry in entries.flatten() {
                let p = entry.path();
                if p.extension().and_then(|e| e.to_str()) != Some("md") {
                    continue;
                }
                match parse_skill_file(&p) {
                    Some(skill) => skills.push(skill),
                    None => warn!(path = %p.display(), "failed to parse skill file"),
                }
            }
            Ok(skills)
        })
        .await
        .map_err(|e| AthenaError::Internal(format!("spawn_blocking: {e}")))?
    }

    async fn get(&self, name: &str) -> Result<Option<Skill>, AthenaError> {
        let skills = self.load_all().await?;
        Ok(skills.into_iter().find(|s| s.name == name))
    }

    async fn technique_map(&self) -> Result<HashMap<String, String>, AthenaError> {
        let skills = self.load_all().await?;
        let mut map = HashMap::new();
        for skill in skills {
            for technique in &skill.techniques {
                map.insert(technique.clone(), skill.content.clone());
            }
            // Also index by skill name for direct lookup
            map.insert(skill.name.clone(), skill.content.clone());
        }
        Ok(map)
    }
}

// ── in-memory implementation (for tests) ─────────────────────────────────────

pub struct InMemorySkillsLoader {
    skills: Vec<Skill>,
}

impl InMemorySkillsLoader {
    pub fn new(skills: Vec<Skill>) -> Self {
        Self { skills }
    }
}

#[async_trait]
impl SkillsLoader for InMemorySkillsLoader {
    async fn load_all(&self) -> Result<Vec<Skill>, AthenaError> {
        Ok(self.skills.clone())
    }

    async fn get(&self, name: &str) -> Result<Option<Skill>, AthenaError> {
        Ok(self.skills.iter().find(|s| s.name == name).cloned())
    }

    async fn technique_map(&self) -> Result<HashMap<String, String>, AthenaError> {
        let mut map = HashMap::new();
        for skill in &self.skills {
            for technique in &skill.techniques {
                map.insert(technique.clone(), skill.content.clone());
            }
            map.insert(skill.name.clone(), skill.content.clone());
        }
        Ok(map)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn make_skill_file(dir: &TempDir, filename: &str, content: &str) -> PathBuf {
        let path = dir.path().join(filename);
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(content.as_bytes()).unwrap();
        path
    }

    #[tokio::test]
    async fn load_skill_with_frontmatter() {
        let dir = TempDir::new().unwrap();
        make_skill_file(&dir, "priv-esc.md", r#"---
name: privilege-escalation
description: Linux privilege escalation techniques
tags: [linux, privesc]
techniques: [T1548, T1166]
---
## Overview
Use SUID binaries to escalate privileges.
"#);
        let loader = FileSystemSkillsLoader::new(dir.path());
        let skills = loader.load_all().await.unwrap();
        assert_eq!(skills.len(), 1);
        assert_eq!(skills[0].name, "privilege-escalation");
        assert_eq!(skills[0].techniques, vec!["T1548", "T1166"]);
        assert!(skills[0].content.contains("SUID"));
    }

    #[tokio::test]
    async fn load_skill_without_frontmatter() {
        let dir = TempDir::new().unwrap();
        make_skill_file(&dir, "recon.md", "Perform network reconnaissance.\n");
        let loader = FileSystemSkillsLoader::new(dir.path());
        let skills = loader.load_all().await.unwrap();
        assert_eq!(skills.len(), 1);
        assert_eq!(skills[0].name, "recon");
        assert!(skills[0].content.contains("reconnaissance"));
    }

    #[tokio::test]
    async fn non_md_files_ignored() {
        let dir = TempDir::new().unwrap();
        make_skill_file(&dir, "notes.txt", "some text");
        make_skill_file(&dir, "skill.md", "# skill\ncontent\n");
        let loader = FileSystemSkillsLoader::new(dir.path());
        let skills = loader.load_all().await.unwrap();
        assert_eq!(skills.len(), 1);
    }

    #[tokio::test]
    async fn get_by_name_returns_correct() {
        let dir = TempDir::new().unwrap();
        make_skill_file(&dir, "a.md", "---\nname: alpha\n---\nalpha content\n");
        make_skill_file(&dir, "b.md", "---\nname: beta\n---\nbeta content\n");
        let loader = FileSystemSkillsLoader::new(dir.path());
        let skill = loader.get("alpha").await.unwrap();
        assert!(skill.is_some());
        assert_eq!(skill.unwrap().name, "alpha");
    }

    #[tokio::test]
    async fn technique_map_indexes_by_technique_id() {
        let loader = InMemorySkillsLoader::new(vec![
            Skill {
                name: "priv-esc".into(),
                description: "".into(),
                content: "suid exploit instructions".into(),
                tags: vec![],
                techniques: vec!["T1548".into()],
            }
        ]);
        let map = loader.technique_map().await.unwrap();
        assert!(map.contains_key("T1548"));
        assert!(map["T1548"].contains("suid"));
    }

    #[tokio::test]
    async fn empty_dir_returns_empty() {
        let dir = TempDir::new().unwrap();
        let loader = FileSystemSkillsLoader::new(dir.path());
        let skills = loader.load_all().await.unwrap();
        assert!(skills.is_empty());
    }
}
