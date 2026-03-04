# {{TOOL_NAME}} — Athena MCP Tool Server

## Quick Start

```bash
pip install -e .
python -m server
```

## Output Convention

Tools must return JSON with Athena-compatible facts:

```json
{
  "facts": [
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "host.os", "value": "Linux"}
  ],
  "raw_output": "..."
}
```

## Adding to Athena

1. Add entry to `mcp_servers.json` at the project root
2. Register in `tool_registry` via `POST /api/tools` with `config_json.mcp_server`
3. Set `MCP_ENABLED=true` in `.env`
