#!/usr/bin/env python3
"""Scaffold a new Athena MCP tool server.

Usage: python scripts/scaffold_tool.py <tool-name>

Steps:
  1. Copy tools/_template/ -> tools/<tool-name>/
  2. Replace {{TOOL_NAME}} placeholders
  3. Inject entry into mcp_servers.json
  4. Inject service into docker-compose.yml (auto-assign port)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML is required: pip install pyyaml")
    sys.exit(1)

PLACEHOLDER = "{{TOOL_NAME}}"
TEMPLATE_EXTENSIONS = {".py", ".toml", ".yaml", ".md"}
PORT_PATTERN = re.compile(r'"127\.0\.0\.1:(\d+):8080"')


def find_project_root() -> Path:
    """Walk up from this script to find the directory containing mcp_servers.json."""
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "mcp_servers.json").exists():
        return candidate
    # Fallback: current working directory
    cwd = Path.cwd()
    if (cwd / "mcp_servers.json").exists():
        return cwd
    print("❌ Cannot find project root (mcp_servers.json not found)")
    sys.exit(1)


def copy_template(template_dir: Path, tool_dir: Path, tool_name: str) -> None:
    """Copy template directory and replace placeholders."""
    shutil.copytree(template_dir, tool_dir)
    for file_path in tool_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in TEMPLATE_EXTENSIONS:
            text = file_path.read_text(encoding="utf-8")
            if PLACEHOLDER in text:
                file_path.write_text(
                    text.replace(PLACEHOLDER, tool_name), encoding="utf-8"
                )


def inject_mcp_servers(
    mcp_file: Path, tool_name: str, tool_yaml: dict
) -> None:
    """Add entry to mcp_servers.json if not already present."""
    data = json.loads(mcp_file.read_text(encoding="utf-8"))
    servers = data.setdefault("servers", {})

    if tool_name in servers:
        print(f"   ⏭  mcp_servers.json → '{tool_name}' already exists, skipped")
        return

    mcp_cfg = tool_yaml.get("mcp", {})
    servers[tool_name] = {
        "transport": mcp_cfg.get("transport", "stdio"),
        "command": mcp_cfg.get("command", "python"),
        "args": mcp_cfg.get("args", ["-m", "server"]),
        "env": {},
        "http_url": mcp_cfg.get("http_url", f"http://mcp-{tool_name}:8080/mcp"),
        "enabled": True,
        "description": tool_yaml.get("description", ""),
        "tool_prefix": mcp_cfg.get("tool_prefix", tool_name),
    }

    mcp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"   ✅ mcp_servers.json → added '{tool_name}'")


def find_next_port(compose_text: str) -> int:
    """Scan docker-compose.yml for used 5809x ports and return the next available."""
    used_ports: set[int] = set()
    for match in PORT_PATTERN.finditer(compose_text):
        used_ports.add(int(match.group(1)))
    candidate = 58091
    while candidate in used_ports:
        candidate += 1
    return candidate


def generate_service_block(
    tool_name: str, port: int, tool_yaml: dict
) -> str:
    """Generate a docker-compose service block for the tool."""
    env_section = ""
    docker_cfg = tool_yaml.get("docker", {})
    docker_env = docker_cfg.get("environment", {})
    if docker_env:
        env_lines = "\n".join(f"      - {k}={v}" for k, v in docker_env.items())
        env_section = f"\n    environment:\n{env_lines}"

    return (
        f"\n  mcp-{tool_name}:\n"
        f"    build: {{ context: ./tools/{tool_name} }}\n"
        f"    profiles: [mcp]\n"
        f'    command: ["python", "-m", "server", "--transport", '
        f'"streamable-http", "--port", "8080"]\n'
        f"{env_section}"
        f"    ports:\n"
        f'      - "127.0.0.1:{port}:8080"\n'
        f"    restart: unless-stopped\n"
    )


def inject_docker_compose(
    compose_file: Path, tool_name: str, tool_yaml: dict
) -> None:
    """Add service block to docker-compose.yml if not already present."""
    text = compose_file.read_text(encoding="utf-8")
    service_name = f"mcp-{tool_name}"

    if service_name in text:
        print(
            f"   ⏭  docker-compose.yml → '{service_name}' already exists, skipped"
        )
        return

    port = find_next_port(text)
    service_block = generate_service_block(tool_name, port, tool_yaml)

    # Insert before the "volumes:" top-level key
    volumes_match = re.search(r"\nvolumes:\n", text)
    if volumes_match:
        insert_pos = volumes_match.start()
        text = text[:insert_pos] + service_block + text[insert_pos:]
    else:
        # Append at end if no volumes section
        text += service_block

    compose_file.write_text(text, encoding="utf-8")
    print(f"   ✅ docker-compose.yml → added '{service_name}' (port {port})")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/scaffold_tool.py <tool-name>")
        sys.exit(1)

    tool_name = sys.argv[1].strip().lower()
    if not tool_name:
        print("❌ Tool name cannot be empty")
        sys.exit(1)

    # Warn about underscores (suggest hyphens)
    if "_" in tool_name:
        print(f"   ⚠️  Consider using hyphens instead of underscores: '{tool_name.replace('_', '-')}'")

    root = find_project_root()
    template_dir = root / "tools" / "_template"
    tool_dir = root / "tools" / tool_name

    # Step 1: Check if already exists
    if tool_dir.exists():
        print(f"❌ Tool '{tool_name}' already exists at {tool_dir}")
        print(f"   Use 'rm -rf {tool_dir}' to remove it first.")
        sys.exit(1)

    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        sys.exit(1)

    # Step 2: Copy template and replace placeholders
    copy_template(template_dir, tool_dir, tool_name)
    print(f"✅ MCP tool scaffold created: tools/{tool_name}/")
    print("   Created:")
    for f in sorted(tool_dir.iterdir()):
        if f.is_file():
            print(f"   - tools/{tool_name}/{f.name}")

    # Step 3: Load tool.yaml for registration data
    tool_yaml_path = tool_dir / "tool.yaml"
    tool_yaml = yaml.safe_load(tool_yaml_path.read_text(encoding="utf-8"))

    # Step 4: Inject into mcp_servers.json
    mcp_file = root / "mcp_servers.json"
    if mcp_file.exists():
        inject_mcp_servers(mcp_file, tool_name, tool_yaml)
    else:
        print(f"   ⚠️  mcp_servers.json not found, skipping registration")

    # Step 5: Inject into docker-compose.yml
    compose_file = root / "docker-compose.yml"
    if compose_file.exists():
        inject_docker_compose(compose_file, tool_name, tool_yaml)
    else:
        print(f"   ⚠️  docker-compose.yml not found, skipping registration")

    # Summary
    print("   Next steps:")
    print(f"   1. Edit tools/{tool_name}/server.py — implement your tool logic")
    print(f"   2. Edit tools/{tool_name}/tool.yaml — fill in metadata (MITRE, traits)")
    print(f"   3. make dev-tool NAME={tool_name} — test locally")
    print(f"   4. make build-mcp — build Docker images")


if __name__ == "__main__":
    main()
