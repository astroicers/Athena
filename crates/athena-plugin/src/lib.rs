use async_trait::async_trait;
use athena_types::AthenaError;
use dashmap::DashMap;
use std::sync::Arc;
use tracing::{info, warn};

// ── trait ─────────────────────────────────────────────────────────────────────

#[async_trait]
pub trait Plugin: Send + Sync {
    fn name(&self) -> &'static str;
    fn version(&self) -> &'static str;
    async fn on_load(&self) -> Result<(), AthenaError>;
    async fn on_unload(&self) -> Result<(), AthenaError>;
}

// ── registry ──────────────────────────────────────────────────────────────────

pub struct PluginRegistry {
    plugins: DashMap<String, Arc<dyn Plugin>>,
}

impl PluginRegistry {
    pub fn new() -> Self {
        Self { plugins: DashMap::new() }
    }

    /// Register a plugin and call on_load. Ignores on_load errors (logged as warnings).
    pub async fn register(&self, plugin: Arc<dyn Plugin>) {
        let name = plugin.name().to_string();
        if let Err(e) = plugin.on_load().await {
            warn!(plugin = %name, err = %e, "on_load failed — plugin registered anyway");
        } else {
            info!(plugin = %name, version = %plugin.version(), "plugin loaded");
        }
        self.plugins.insert(name, plugin);
    }

    /// Unregister a plugin and call on_unload.
    pub async fn unregister(&self, name: &str) -> Result<(), AthenaError> {
        match self.plugins.remove(name) {
            Some((_, plugin)) => {
                plugin.on_unload().await?;
                info!(plugin = %name, "plugin unloaded");
                Ok(())
            }
            None => Err(AthenaError::OperationNotFound(format!("plugin not found: {name}"))),
        }
    }

    pub fn get(&self, name: &str) -> Option<Arc<dyn Plugin>> {
        self.plugins.get(name).map(|p| p.clone())
    }

    pub fn list(&self) -> Vec<String> {
        self.plugins.iter().map(|e| e.key().clone()).collect()
    }

    pub fn len(&self) -> usize {
        self.plugins.len()
    }

    pub fn is_empty(&self) -> bool {
        self.plugins.is_empty()
    }
}

impl Default for PluginRegistry {
    fn default() -> Self { Self::new() }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicBool, Ordering};

    struct FakePlugin {
        loaded: AtomicBool,
    }

    impl FakePlugin {
        fn new() -> Arc<Self> { Arc::new(Self { loaded: AtomicBool::new(false) }) }
    }

    #[async_trait]
    impl Plugin for FakePlugin {
        fn name(&self) -> &'static str { "fake" }
        fn version(&self) -> &'static str { "0.1.0" }
        async fn on_load(&self) -> Result<(), AthenaError> {
            self.loaded.store(true, Ordering::Relaxed);
            Ok(())
        }
        async fn on_unload(&self) -> Result<(), AthenaError> {
            self.loaded.store(false, Ordering::Relaxed);
            Ok(())
        }
    }

    struct BrokenPlugin;
    #[async_trait]
    impl Plugin for BrokenPlugin {
        fn name(&self) -> &'static str { "broken" }
        fn version(&self) -> &'static str { "0.0.1" }
        async fn on_load(&self) -> Result<(), AthenaError> {
            Err(AthenaError::Internal("load failed".into()))
        }
        async fn on_unload(&self) -> Result<(), AthenaError> { Ok(()) }
    }

    #[tokio::test]
    async fn register_and_get() {
        let reg = PluginRegistry::new();
        let plugin = FakePlugin::new();
        reg.register(Arc::clone(&plugin) as Arc<dyn Plugin>).await;
        assert!(reg.get("fake").is_some());
        assert!(plugin.loaded.load(Ordering::Relaxed));
    }

    #[tokio::test]
    async fn unregister_removes_plugin() {
        let reg = PluginRegistry::new();
        reg.register(FakePlugin::new() as Arc<dyn Plugin>).await;
        assert_eq!(reg.len(), 1);
        reg.unregister("fake").await.unwrap();
        assert!(reg.is_empty());
    }

    #[tokio::test]
    async fn unregister_unknown_returns_err() {
        let reg = PluginRegistry::new();
        let result = reg.unregister("nonexistent").await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn broken_on_load_still_registers() {
        let reg = PluginRegistry::new();
        reg.register(Arc::new(BrokenPlugin) as Arc<dyn Plugin>).await;
        assert!(reg.get("broken").is_some());
    }

    #[tokio::test]
    async fn list_returns_all_names() {
        let reg = PluginRegistry::new();
        reg.register(FakePlugin::new() as Arc<dyn Plugin>).await;
        let names = reg.list();
        assert!(names.contains(&"fake".to_string()));
    }
}
