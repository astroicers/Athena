# vuln-lookup — Athena MCP Tool Server

CVE lookup via NVD NIST API and CPE mapping as MCP tools.

## Quick Start

```bash
pip install -e .
python -m server
```

## Tools

### banner_to_cpe

Convert a service banner to a CPE 2.2 string.

**Parameters:**
- `service` (str): Service name from nmap (e.g., "ssh", "http")
- `version` (str): Version string from nmap banner (e.g., "OpenSSH 7.4")

### nvd_cve_lookup

Query NVD NIST API v2 for CVEs matching a CPE string.

**Parameters:**
- `cpe` (str): CPE 2.2 string (e.g., "cpe:/a:openbsd:openssh:7.4")
- `max_results` (int, optional): Maximum CVEs to return (default: 10)

## Environment Variables

- `NVD_API_KEY` (optional): NVD API key for higher rate limits

## Output Convention

```json
{
  "facts": [
    {"trait": "vuln.cpe", "value": "cpe:/a:openbsd:openssh:7.4"},
    {"trait": "vuln.cve", "value": "CVE-2023-1234:cvss=7.5:severity=high:exploit=false:desc=..."}
  ],
  "raw_output": "Found 3 CVEs for cpe:/a:openbsd:openssh:7.4"
}
```

## Adding to Athena

1. Add entry to `mcp_servers.json` at the project root
2. Register in `tool_registry` via `POST /api/tools` with `config_json.mcp_server`
3. Set `MCP_ENABLED=true` in `.env`
