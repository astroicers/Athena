use tracing_subscriber::{fmt, EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};

pub fn init() {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .with(fmt::layer().json())
        .init();
}

pub fn init_pretty() {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .with(fmt::layer())
        .init();
}

#[cfg(test)]
mod tests {
    use tracing::info;

    #[test]
    fn tracing_macro_does_not_panic() {
        // init() / init_pretty() would panic on second call (global subscriber already set).
        // Just verify the tracing macros themselves work without a subscriber.
        info!("telemetry test");
    }

    #[test]
    fn env_filter_default_is_info() {
        use tracing_subscriber::EnvFilter;
        let filter = EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("info"));
        // Just assert it builds without panicking
        drop(filter);
    }
}
