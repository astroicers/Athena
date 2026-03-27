# Athena Roadmap

## v0.1.0 (Released) — Enterprise External Pentest MVP

### Completed

- OODA automated loop (APScheduler-driven, auto-start/stop/status endpoints)
- OSINT subdomain enumeration (crt.sh + subfinder)
- Nmap Recon + CVE correlation (NVD API, 24h cache)
- SSH credential spraying (DirectSSHEngine) + Persistent Session Pool (PersistentSSHChannelEngine)
- Metasploit RPC integration (vsftpd / UnrealIRCd / Samba / WinRM) with MOCK_METASPLOIT=true CI default
- Playbook CRUD API (13 seed playbooks, dynamic output_parser)
- Structured reporting (JSON + Markdown)
- ROE / Scope validation (ScopeValidator)
- C5ISR battle dashboard (WebSocket)

## v0.2.0 (Released) — Lateral Movement + Persistence

### Completed (Phase G)

- SSH key-based auth (`credential.ssh_key` fact, `user@host:port#<base64_key>` format)
- Lateral movement technique mapping (T1021.004_priv/recon, T1560.001, T1105)
- Auto-mark target `is_compromised` + `privilege_level` on successful SSH execution
- OrientEngine Section 7.7 — lateral movement opportunity recommendations (credentials × uncompromised targets)
- 17 seed playbooks (13 recon + 4 lateral movement)
- output_parser wiring: playbook-defined output_parser passed to SSH execution engines

### Completed (Phase H)

- Linux persistence probe — PersistenceEngine (T1053.003 cron, T1543.002 systemd) with `PERSISTENCE_ENABLED` toggle
- Windows WinRM post-exploitation — WinRMEngine (pywinrm + mock mode, `WINRM_ENABLED` toggle, 7 PowerShell techniques)
- 25 seed playbooks (+ T1136.001 account, + 3 Windows WinRM, + 2 Linux persistence)
- OrientEngine Section 7.6 platform-aware (Windows vs Linux playbook selection based on target OS)
- OrientEngine Section 7.7 persistence status (host.persistence facts surfaced to LLM)

### Completed (Phase I)

- Agent capability matching — `AgentCapabilityMatcher` selects best-fit C2 agent by privilege (SYSTEM > Admin > User) + platform; replaces blind `LIMIT 1` selection (ADR-021, SPEC-022)
- Tech debt: `_get_output_parser` now platform-aware (`platform='windows'` for WinRM path); seed INSERT bug fixed (output_parser column was missing)
- 202 tests passing

## v0.3.0 (Released) — C5ISR + Attack Graph + MCP Tools

### Completed (Phase 10-11)

- PostgreSQL migration (asyncpg + Alembic, replaced SQLite)
- Attack Graph engine with YAML-based technique rules (13 rules, Dijkstra weighted paths)
- C5ISR 6-domain battle dashboard (Command/Control/Comms/Computers/Cyber/ISR)
- Constraint engine (mission profile-aware noise/risk thresholds)
- OPSEC monitoring (noise tracking, threat level computation, cross-domain penalty)
- MCP tool servers: nmap-scanner, osint-recon, vuln-lookup, credential-checker, attack-executor, web-scanner, api-fuzzer, msf-rpc
- Tool Registry with enable/disable toggle, health checks, and execution API
- Vulnerability management module (severity heat strip, status pipeline, PoC evidence)
- Engagement/ROE lifecycle (draft -> active -> suspended)
- Dashboard aggregate APIs (kill-chain, attack-surface, time-series, credential-graph)
- Structured pentest report (JSON + Markdown export)
- OODA directive system (operator guidance for orient phase)
- Batch target import (CIDR/IP/hostname, max 512)
- Network topology visualization
- Web Terminal (SSH interactive console for compromised targets)
- Notification center
- 158+ E2E tests (Playwright), 370+ backend tests (pytest), 63+ frontend unit tests (Vitest)

## v0.4.0 (Planned) — Advanced Orchestration

### Priority 1: SPEC-039 — Attack Graph YAML Externalization + 50 Rules
### Priority 2: SPEC-032 — mcp-web-scanner (httpx + Nuclei)
### Priority 3: SPEC-028 Phase 4 — ExploitValidator SafeProbe
### Priority 4: SPEC-044 — Vulnerability Dynamic Validation Pipeline
### Priority 5: SPEC-027 — UI Optimization (5 phases)

## v1.0.0 (Future) — Production Ready

- Authentication & RBAC (JWT + Commander/Operator/Observer roles)
- Multi-operation support (sidebar switcher, cross-op intelligence sharing)
- Advanced topology (VR mode, attack path replay)
- PDF report generation + MITRE coverage heatmap export
- External integrations (BloodHound, Cobalt Strike, Slack/Teams notifications)
- Helm Chart for Kubernetes deployment
