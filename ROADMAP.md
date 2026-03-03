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

## v0.3.0 (Planned) — Advanced Orchestration

- Multi-stage campaign automation (ADR required)
- Attack graph visualization (ADR required)
- Custom playbook editor UI (ADR required)
