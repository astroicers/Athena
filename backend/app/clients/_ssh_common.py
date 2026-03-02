# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared SSH utilities for DirectSSHEngine and PersistentSSHChannelEngine."""

from typing import Any

# MITRE ID → SSH command mapping. {target_ip} replaced at runtime.
TECHNIQUE_EXECUTORS: dict[str, str] = {
    "T1592": "uname -a && id && cat /etc/os-release",
    "T1046": "netstat -tulnp 2>/dev/null || ss -tulnp 2>/dev/null",
    "T1059.004": "bash -c 'id && whoami && hostname'",
    "T1003.001": "cat /etc/shadow 2>/dev/null || echo 'NO_SHADOW_ACCESS'",
    "T1087": "cat /etc/passwd | cut -d: -f1,3,7",
    "T1083": "find / -name '*.conf' -readable 2>/dev/null | head -20",
    "T1190": "curl -sI http://localhost/ 2>/dev/null | head -5",
    "T1595.001": "echo 'NMAP_LOCAL_ONLY'",
    "T1595.002": "echo 'NMAP_LOCAL_ONLY'",
    "T1021.004": "id && hostname",
    "T1078.001": "id && cat /etc/passwd | grep -v nologin | grep -v false",
    "T1110.001": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
    "T1110.003": "echo 'HANDLED_BY_INITIAL_ACCESS_ENGINE'",
}

TECHNIQUE_FACT_TRAITS: dict[str, list[str]] = {
    "T1592": ["host.os", "host.user"],
    "T1046": ["service.open_port"],
    "T1059.004": ["host.process"],
    "T1003.001": ["credential.hash"],
    "T1087": ["host.user"],
    "T1083": ["host.file"],
    "T1190": ["service.web"],
    "T1595.001": ["network.host.ip"],
    "T1595.002": ["vuln.cve"],
    "T1021.004": ["host.session"],
    "T1078.001": ["credential.ssh"],
    "T1110.001": ["credential.ssh"],
    "T1110.003": ["credential.ssh"],
}


def _parse_credential(cred_value: str) -> tuple[str, str, str, int]:
    """Parse 'user:pass@host:port' or 'user:pass' → (user, pass, host, port)."""
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


def _parse_stdout_to_facts(mitre_id: str, stdout: str) -> list[dict[str, Any]]:
    """Extract facts from command stdout based on technique type."""
    facts = []
    traits = TECHNIQUE_FACT_TRAITS.get(mitre_id, [])
    for trait in traits:
        if not stdout.strip():
            continue
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if lines:
            facts.append({
                "trait": trait,
                "value": lines[0][:500],
                "score": 1,
                "source": "direct_ssh",
            })
    return facts
