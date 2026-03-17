# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Shared SSH credential parsers.

Technique executors and fact extraction have moved to the
mcp-attack-executor MCP server (tools/attack-executor/server.py).
Only credential parsers remain here for use by persistence_engine.py.
"""

import base64


def _parse_credential(cred_value: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' or 'user:pass' → (user, pass, host, port).

    Raises ``ValueError`` if *cred_value* does not look like a credential
    (e.g. command output accidentally stored with the wrong fact trait).
    """
    if cred_value.startswith("uid=") or "\n" in cred_value:
        raise ValueError(
            f"Value does not look like a credential: {cred_value[:80]}"
        )
    host = ""
    port = 22
    if "@" in cred_value:
        user_pass, host_port = cred_value.rsplit("@", 1)
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            host = host_port
    else:
        user_pass = cred_value

    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
    else:
        user, password = user_pass, ""

    return user, password, host, port


def _parse_key_credential(target: str) -> tuple[str, str, int, str]:
    """Parse 'user@host:port#<base64_private_key>' format.

    Returns (username, host, port, key_content).
    Raises ValueError if the format is invalid or base64 decoding fails.
    """
    try:
        conn_part, key_b64 = target.split("#", 1)
        key_content = base64.b64decode(key_b64).decode()
        user, hostport = conn_part.split("@", 1)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = hostport, 22
        return user, host, port, key_content
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc
    except Exception as exc:  # binascii.Error from b64decode
        raise ValueError(f"Invalid ssh_key credential format: {exc}") from exc
