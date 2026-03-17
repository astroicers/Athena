# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Central loader for all externalized security knowledge tables.

Pattern mirrors attack_graph_engine._load_rules():
  - functools.cache for in-process caching
  - reload_all() for hot-reload
  - Raises FileNotFoundError clearly on missing files (no silent fallback)
"""
import functools
import logging
from pathlib import Path
from typing import Any

import yaml

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
logger = logging.getLogger(__name__)


@functools.cache
def _load(filename: str) -> Any:
    path = _DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def reload_all() -> None:
    """Clear all cached knowledge tables (pick up YAML edits without restart)."""
    _load.cache_clear()
    logger.info("knowledge_base: all tables reloaded")


def get_exploitable_banners() -> dict[str, str]:
    """Banner substring -> Metasploit service name. Source: engine_router."""
    return _load("exploitable_banners.yaml").get("banners", {})


def get_backport_patterns() -> list[dict]:
    """Distro backport detection patterns. Source: exploit_validator."""
    return _load("backport_patterns.yaml").get("patterns", [])


def get_weaponized_cves() -> list[dict]:
    """Well-known weaponized CVEs for auto-confirmation. Source: exploit_validator."""
    return _load("weaponized_cves.yaml").get("cves", [])


def get_cve_prerequisites() -> dict[str, list[str]]:
    """CVE-specific required facts. Source: exploit_validator."""
    return _load("cve_prerequisites.yaml").get("prerequisites", {})


def get_cpe_mappings() -> dict[str, list[str]]:
    """Service name -> [CPE vendor, CPE product]. Source: vuln_lookup."""
    return _load("cpe_mappings.yaml").get("mappings", {})


def get_noise_risk_matrix() -> dict[str, dict[str, bool | None]]:
    """Decision matrix: profile -> '{noise}_{risk}' -> bool|None. Source: decision_engine."""
    return _load("noise_risk_matrix.yaml").get("matrix", {})


def get_kill_chain_stages() -> list[dict]:
    """MITRE ATT&CK kill chain stage definitions. Source: kill_chain_enforcer."""
    return _load("kill_chain_stages.yaml").get("stages", [])


def get_default_credentials() -> dict[str, list[list[str]]]:
    """Default credentials by protocol. Source: initial_access_engine."""
    return _load("default_credentials.yaml").get("credentials", {})


def get_protocol_map() -> list[dict]:
    """Protocol detection table: port/service/protocol/tool. Source: initial_access_engine."""
    return _load("protocol_map.yaml").get("protocols", [])
