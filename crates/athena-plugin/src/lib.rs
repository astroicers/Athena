use async_trait::async_trait;
use athena_types::AthenaError;
use dashmap::DashMap;
use std::sync::Arc;

#[async_trait]
pub trait Plugin: Send + Sync {
    fn name(&self) -> &'static str;
    fn version(&self) -> &'static str;
    async fn on_load(&self) -> Result<(), AthenaError>;
    async fn on_unload(&self) -> Result<(), AthenaError>;
}

pub struct PluginRegistry {
    plugins: DashMap<String, Arc<dyn Plugin>>,
}

impl PluginRegistry {
    pub fn new() -> Self {
        Self { plugins: DashMap::new() }
    }

    pub fn register(&self, plugin: Arc<dyn Plugin>) {
        self.plugins.insert(plugin.name().to_string(), plugin);
    }

    pub fn get(&self, name: &str) -> Option<Arc<dyn Plugin>> {
        self.plugins.get(name).map(|p| p.clone())
    }
}

impl Default for PluginRegistry {
    fn default() -> Self { Self::new() }
}
