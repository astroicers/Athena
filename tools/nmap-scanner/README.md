# nmap-scanner — Athena MCP Tool Server

Nmap port scanning and service detection as an MCP tool.

## Quick Start

```bash
pip install -e .
python -m server
```

## Tools

### nmap_scan

Run nmap service/version scan against a target IP.

**Parameters:**
- `target` (str): IP address or hostname to scan
- `ports` (str, optional): Comma-separated port list (defaults to common ports)

**Output facts:**
- `service.open_port`: `"{port}/{proto}/{service}/{version}"`
- `network.host.ip`: target IP address
- `host.os`: OS guess (if detected)

## Output Convention

```json
{
  "facts": [
    {"trait": "service.open_port", "value": "22/tcp/ssh/OpenSSH_7.4"},
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "host.os", "value": "Linux_2.6.x"}
  ],
  "raw_output": "..."
}
```

## Adding to Athena

1. Add entry to `mcp_servers.json` at the project root
2. Register in `tool_registry` via `POST /api/tools` with `config_json.mcp_server`
3. Set `MCP_ENABLED=true` in `.env`
