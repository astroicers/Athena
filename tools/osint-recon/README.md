# osint-recon — Athena MCP Tool Server

OSINT subdomain enumeration and DNS resolution as MCP tools.

## Quick Start

```bash
pip install -e .
python -m server
```

## Tools

### crtsh_query

Query crt.sh certificate transparency logs for subdomains.

**Parameters:**
- `domain` (str): Apex domain to enumerate (e.g., "example.com")

### subfinder_query

Run subfinder binary for subdomain enumeration. Gracefully degrades if subfinder is not installed.

**Parameters:**
- `domain` (str): Apex domain to enumerate

### dns_resolve

DNS A/AAAA resolution for a comma-separated list of subdomains.

**Parameters:**
- `subdomains` (str): Comma-separated list of subdomains to resolve

## Output Convention

```json
{
  "facts": [
    {"trait": "osint.subdomain", "value": "www.example.com"},
    {"trait": "osint.resolved_ip", "value": "www.example.com:93.184.216.34"}
  ],
  "raw_output": "Found 5 subdomains via crt.sh"
}
```

## Adding to Athena

1. Add entry to `mcp_servers.json` at the project root
2. Register in `tool_registry` via `POST /api/tools` with `config_json.mcp_server`
3. Set `MCP_ENABLED=true` in `.env`
