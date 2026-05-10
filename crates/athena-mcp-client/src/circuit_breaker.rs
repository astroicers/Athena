use std::sync::Mutex;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CircuitState {
    Closed,   // normal — requests pass through
    Open,     // tripped — requests fail fast
    HalfOpen, // probe — one request allowed through to test recovery
}

pub struct CircuitBreaker {
    state: Mutex<CircuitState>,
    failure_count: Mutex<u32>,
    last_failure: Mutex<Option<Instant>>,
    failure_threshold: u32,
    recovery_timeout: Duration,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: u32, recovery_timeout_secs: u64) -> Self {
        Self {
            state: Mutex::new(CircuitState::Closed),
            failure_count: Mutex::new(0),
            last_failure: Mutex::new(None),
            failure_threshold,
            recovery_timeout: Duration::from_secs(recovery_timeout_secs),
        }
    }

    pub fn state(&self) -> CircuitState {
        // Check open→half-open transition without holding both locks simultaneously
        let is_open = {
            matches!(*self.state.lock().unwrap(), CircuitState::Open)
        };
        if is_open {
            let elapsed_past_timeout = {
                let last = self.last_failure.lock().unwrap();
                last.map(|t| t.elapsed() >= self.recovery_timeout).unwrap_or(false)
            };
            if elapsed_past_timeout {
                *self.state.lock().unwrap() = CircuitState::HalfOpen;
                return CircuitState::HalfOpen;
            }
            return CircuitState::Open;
        }
        self.state.lock().unwrap().clone()
    }

    pub fn is_open(&self) -> bool {
        self.state() == CircuitState::Open
    }

    pub fn record_success(&self) {
        *self.state.lock().unwrap() = CircuitState::Closed;
        *self.failure_count.lock().unwrap() = 0;
    }

    pub fn record_failure(&self) {
        let mut count = self.failure_count.lock().unwrap();
        *count += 1;
        *self.last_failure.lock().unwrap() = Some(Instant::now());
        if *count >= self.failure_threshold {
            *self.state.lock().unwrap() = CircuitState::Open;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starts_closed() {
        let cb = CircuitBreaker::new(3, 60);
        assert_eq!(cb.state(), CircuitState::Closed);
        assert!(!cb.is_open());
    }

    #[test]
    fn opens_after_threshold_failures() {
        let cb = CircuitBreaker::new(3, 60);
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Closed);
        cb.record_failure(); // 3rd = threshold
        assert_eq!(cb.state(), CircuitState::Open);
        assert!(cb.is_open());
    }

    #[test]
    fn success_resets_to_closed() {
        let cb = CircuitBreaker::new(2, 60);
        cb.record_failure();
        cb.record_failure();
        assert!(cb.is_open());
        cb.record_success();
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    #[test]
    fn transitions_to_half_open_after_timeout() {
        // Use 1s recovery timeout; immediately after tripping it should be Open,
        // then after sleeping past the timeout it transitions to HalfOpen.
        let cb = CircuitBreaker::new(1, 1);
        cb.record_failure();
        // Immediately after trip: still Open (1s hasn't elapsed)
        assert_eq!(cb.state(), CircuitState::Open);
        // With 0s timeout variant we can force: set recovery_timeout = 0 via a fresh CB,
        // record failure, then sleep 5ms to pass the timeout
        let cb2 = CircuitBreaker::new(1, 0);
        cb2.record_failure();
        std::thread::sleep(Duration::from_millis(10));
        assert_eq!(cb2.state(), CircuitState::HalfOpen);
    }
}
