# Changelog

All notable changes to Athena 2.0 are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `POST /operations/:op_id/approve` — human approval gate for high-risk OODA iterations; writes `human_approved` fact that DecidePhase detects to bypass risk threshold
- `POST /operations/:op_id/iterate` now accepts `StartOperationRequest` body, enabling `operator_override` mode on existing operations
- `SshTargetConfig` in `athena-config` — SSH credentials and port loaded from `[ssh]` section in `athena.toml`; all fields have serde defaults so existing configs without `[ssh]` still load cleanly
- `StreamableMcpClient` — standard MCP StreamableHTTP transport replacing the custom REST client; supports per-tool base URLs, circuit breaker, and session retry on stale TCP
- `PhaseContext` pipeline (ADR-118) — shared state bag passed through all OODA phases; `extensions: HashMap<String, Value>` for inter-phase communication (operator_override, human_approved)
- `GET /api/operations` — lists all operations with OODA iteration counts
- `IterationStore::record(op_id, iter_id, op_name)` — persists OODA iterations to `ooda_iterations` table in postgres
- `ActRouter::resolve_target()` — reads `target_ip` / `target_hostname` facts from fact_repo; no longer uses empty dummy target
- `SshExecutionEngine::supports_technique()` — pre-flight check before attempting SSH connection
- Operator override mode — bypasses LLM Orient and risk gate; executes operator-specified MITRE techniques directly
- Diagrams directory `docs/diagrams/` — OODA pipeline, crate dependency, API routes mindmap

### Fixed
- `pool_max_idle_per_host(0)` in `StreamableMcpClient` — prevents stale TCP reuse to long-running Docker containers
- MCP session cache eviction + retry on transport error — handles container restarts gracefully
- Legacy KEX algorithms (`DH_G1_SHA1`, `DH_G14_SHA1`) and host key (`SSH_RSA`) added to `russh::Preferred` — enables SSH against OpenSSH < 7.0 (e.g. Metasploitable 2 / OpenSSH 4.7p1)
- C5ISR scoring now uses prefix-aware `has()` / `count_prefix()` — `service.open_port` correctly matches `open_port` prefix; overall score 13% → 52% for Metasploitable 2
- Report `severity_for_trait()` returns `Option<Severity>` — metadata facts (`target_ip`, `human_approved`, `operator_override`) are skipped; prefix matching for `service.open_port` and `network.host.*`
- `facts_collected` in API response counts fact_repo delta across the full OODA cycle
- OAuth token uses `Authorization: Bearer` header (not `x-api-key`)
- ACT success log now includes `output=` field for shell command result visibility

### Changed
- `athena-config` `AthenaConfig` gains `ssh: SshTargetConfig` field — `main.rs` now builds `SshExecutionEngine` from config instead of `SshConfig::default()`
- ADR-118 status: Draft → Accepted

## [2.0.0-alpha.1] — 2026-04-xx

### Added
- Full Rust rewrite: 41-crate Cargo workspace
- OODA engine (`athena-engine-ooda`) — Observe → Orient → Decide → Act state machine
- `SqlxFactRepository` + `SqlxIterationStore` — postgres-backed fact and iteration persistence
- `ClaudeOrientEngine` — LLM-driven threat analysis via Anthropic API (OAuth + API key)
- `RiskMatrixDecider` — risk-threshold gating with configurable deny-list
- `DefaultObserver` — seeds `target_ip` fact from API, drives nmap MCP scan
- `SshExecutionEngine` — russh-based SSH execution for 15+ MITRE techniques
- `McpFactExtractor` — normalises FastMCP `{"facts":[...]}` and legacy `{"open_ports":[...]}` formats
- `FactDrivenC5isrMapper` — 6-domain C5ISR scores derived from collected facts
- `FactReportGenerator` — pentest report with severity-sorted findings in Markdown and JSON
- `athena-pentest-kb` — Tantivy full-text knowledge base loaded from `data/kb/` markdown files
- `athena-attack-graph` — Dijkstra-based attack path computation
- All 27 API routes via axum — health, operations, facts, observe, orient, decide, act, scheduler, scope, opsec, c5isr, vuln, kb, brief, report, recon, ws
- `POST /api/operations` accepts `target_ip` / `target_hostname` body; injects seed facts before first OODA cycle
- docker-compose.mcp.yml — launches 7 MCP tool containers in streamable-http mode (ports 9101–9107)
- ADR-100 through ADR-118 (all Accepted)
