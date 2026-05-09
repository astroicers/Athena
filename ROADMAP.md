# Athena Roadmap

> **For the detailed phase-by-phase development plan (Chinese), see [`docs/ROADMAP.md`](docs/ROADMAP.md).**

This file gives a quick release-level snapshot. The authoritative, regularly-updated breakdown lives in `docs/ROADMAP.md`.

## Released

| Version | Theme | Highlights |
|---------|-------|-----------|
| **v0.1.0** | Enterprise External Pentest MVP | OODA loop, OSINT enum, Nmap+CVE, SSH spraying, Metasploit RPC, 13 seed playbooks, C5ISR dashboard |
| **v0.2.0** | Lateral Movement + Persistence | SSH key auth, lateral movement mapping, Linux persistence, Windows WinRM, agent capability matching, 25 seed playbooks |
| **v0.3.0** | C5ISR + Attack Graph + MCP Tools | PostgreSQL migration, Attack Graph engine (13 rules), 20 MCP tool servers, vuln management, OODA directives, network topology, web terminal |

## Planned

- **v0.4.0** — Advanced Orchestration: Attack Graph YAML externalization (50 rules), `mcp-web-scanner`, ExploitValidator SafeProbe, vulnerability dynamic validation, UI optimization
- **v1.0.0** — Production: Auth & RBAC, multi-operation support, advanced topology, PDF reports, external integrations (BloodHound, Cobalt Strike), Helm chart

For the full phase tracker (Phase 0–12.7) and per-SPEC progress, refer to [`docs/ROADMAP.md`](docs/ROADMAP.md).
