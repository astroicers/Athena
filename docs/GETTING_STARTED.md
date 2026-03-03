# Getting Started with Athena

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| pip | latest | Package management |
| SQLite | 3.35+ | Database (bundled with Python) |
| (Optional) Metasploit Framework | 6.x | Live exploit execution |
| (Optional) subfinder | any | Subdomain enumeration |
| (Optional) nmap | 7.x | Port scanning |

## Quick Start (Development)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/Athena.git
cd Athena

# 2. Create virtualenv and install dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# 4. Start the server
uvicorn app.main:app --reload --port 8000

# 5. Verify
curl http://localhost:8000/api/health
```

## Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Claude API key for OODA Orient phase |
| `MOCK_LLM` | `false` | Use mock LLM (no API calls) for dev/CI |
| `MOCK_C2_ENGINE` | `false` | Use mock C2 (no Caldera) for dev/CI |
| `MOCK_METASPLOIT` | `true` | Use mock Metasploit (no msfrpcd) for dev/CI |
| `OODA_LOOP_INTERVAL_SEC` | `30` | Seconds between OODA auto-loop cycles |
| `MSF_RPC_HOST` | `127.0.0.1` | Metasploit RPC host |
| `MSF_RPC_PORT` | `55553` | Metasploit RPC port |
| `MSF_RPC_USER` | `msf` | Metasploit RPC username |
| `MSF_RPC_PASSWORD` | *(required in live mode)* | Metasploit RPC password |
| `MSF_RPC_SSL` | `false` | Enable SSL for Metasploit RPC |

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -q
# Expected: 143+ passed, 6 skipped
```

## Connecting Metasploit (Live Mode)

For live exploit execution against real targets:

```bash
# Start msfrpcd
msfrpcd -P your_password -U msf -a 127.0.0.1

# Update .env
MOCK_METASPLOIT=false
MSF_RPC_PASSWORD=your_password

# Restart Athena
uvicorn app.main:app --reload --port 8000
```

Supported modules:

| Service | Metasploit Module |
|---------|------------------|
| vsftpd 2.3.4 | `exploit/unix/ftp/vsftpd_234_backdoor` |
| UnrealIRCd 3.2.8.1 | `exploit/unix/irc/unreal_ircd_3281_backdoor` |
| Samba < 3.0.20 | `exploit/multi/samba/usermap_script` |
| WinRM | `auxiliary/scanner/winrm/winrm_login` |

## API Reference

Interactive API docs: `http://localhost:8000/docs`

Key endpoints:

- `POST /api/operations` — Create operation
- `POST /api/operations/{id}/targets` — Add target to operation
- `POST /api/operations/{id}/ooda/auto-start` — Start OODA auto loop
- `GET /api/operations/{id}/ooda/auto-status` — Check loop status
- `DELETE /api/operations/{id}/ooda/auto-stop` — Stop loop
- `GET /api/playbooks` — List technique playbooks
- `GET /api/operations/{operation_id}/report` — Generate report
