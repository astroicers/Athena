# lateral-mover — Athena MCP Tool Server

## Quick Start

### 1. Scaffold (already done if you see this file)

```bash
make new-tool NAME=lateral-mover
```

### 2. Implement tool logic

Edit `server.py` — replace `example_scan` with your tool function(s).

**Output convention:** Return JSON string with Athena-compatible facts:

```json
{
  "facts": [
    {"trait": "network.host.ip", "value": "10.0.1.5"},
    {"trait": "host.os", "value": "Linux"}
  ],
  "raw_output": "Human-readable scan output..."
}
```

### 3. Fill in metadata

Edit `tool.yaml` — set description, category, mitre_techniques, output_traits.

### 4. Test locally

```bash
make dev-tool NAME=lateral-mover           # stdio mode
make dev-tool-http NAME=lateral-mover      # HTTP mode (port 8090)
```

### 5. Build & Deploy

```bash
make build-mcp
docker compose --profile mcp up -d
```

MCPClientManager will auto-discover tools and sync to tool_registry DB.

## Dependencies

Add Python dependencies to `pyproject.toml` under `[project] dependencies`.

If system packages are needed (e.g. nmap), add them to `Dockerfile`:

```dockerfile
FROM athena-mcp-base:latest
RUN apt-get update && apt-get install -y --no-install-recommends <package> && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
CMD ["python", "-m", "server"]
```
