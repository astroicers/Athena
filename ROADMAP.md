# Athena Roadmap

## v0.1.0 (Current) — Enterprise External Pentest MVP

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

## v0.2.0 (Planned) — Lateral Movement + Persistence

- Multi-agent coordination (agent capability matching)
- Persistence implants (cron, scheduled tasks, systemd)
- Lateral movement routing (agent-to-agent tunneling)
- Windows WinRM post-exploitation via MetasploitRPCEngine
- output_parser wiring: playbook-defined output_parser passed to SSH execution engines

## v0.3.0 (Planned) — Full Reporting + Cloud Deployment

- Auto-report generation on operation completion
- Report template customization (Jinja2)
- AWS / Azure deployment guide
- SAML/OIDC auth integration
- Operator RBAC (role-based access control)
