# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Multi-relay router — select the optimal relay for a target by subnet matching.

tech-debt: test-pending — unit tests needed for RelayRouter.select_relay()
    (subnet match, catch-all, legacy fallback, no relay). Vibe-coding workflow
    exemption (ASP).
"""

import ipaddress
import json
import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RelayConfig:
    """Configuration for a single relay node."""

    name: str
    ip: str
    ssh_user: str = "athena-relay"
    ssh_port: int = 22
    lport: int = 4444
    subnet: str = ""  # e.g. "10.0.1.0/24" — empty means "catch-all"


def _parse_relay_configs() -> list[RelayConfig]:
    """Parse RELAY_CONFIGS JSON string into a list of RelayConfig objects."""
    raw = settings.RELAY_CONFIGS or ""
    if not raw.strip():
        return []
    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            logger.warning("RELAY_CONFIGS is not a JSON array, ignoring")
            return []
        configs = []
        for item in items:
            configs.append(RelayConfig(
                name=item.get("name", "unnamed"),
                ip=item.get("ip", ""),
                ssh_user=item.get("ssh_user", settings.RELAY_SSH_USER),
                ssh_port=item.get("ssh_port", settings.RELAY_SSH_PORT),
                lport=item.get("lport", settings.RELAY_LPORT),
                subnet=item.get("subnet", ""),
            ))
        return configs
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse RELAY_CONFIGS: %s", e)
        return []


# Module-level cached configs (parsed once at import time, avoids re-parsing
# JSON on every RelayRouter instantiation in hot paths like _execute_metasploit).
_CACHED_RELAY_CONFIGS: list[RelayConfig] = _parse_relay_configs()


class RelayRouter:
    """Route relay selection based on target IP subnet matching."""

    def __init__(self) -> None:
        self._configs: list[RelayConfig] = _CACHED_RELAY_CONFIGS

    def select_relay(self, target_ip: str) -> RelayConfig | None:
        """Select the best relay for a given target IP.

        1. Try subnet match from RELAY_CONFIGS
        2. Fallback to legacy single RELAY_IP
        3. Return None if no relay is available
        """
        # Try multi-relay subnet matching
        if self._configs:
            try:
                target = ipaddress.ip_address(target_ip)
            except ValueError:
                logger.warning("Invalid target IP for relay selection: %s", target_ip)
                target = None

            if target:
                # First pass: exact subnet match
                for cfg in self._configs:
                    if cfg.subnet:
                        try:
                            network = ipaddress.ip_network(cfg.subnet, strict=False)
                            if target in network:
                                logger.info(
                                    "Relay '%s' (%s) selected for target %s (subnet %s)",
                                    cfg.name, cfg.ip, target_ip, cfg.subnet,
                                )
                                return cfg
                        except ValueError:
                            continue

                # Second pass: catch-all relay (no subnet specified)
                for cfg in self._configs:
                    if not cfg.subnet and cfg.ip:
                        logger.info(
                            "Relay '%s' (%s) selected as catch-all for target %s",
                            cfg.name, cfg.ip, target_ip,
                        )
                        return cfg

        # Fallback to legacy single RELAY_IP
        if settings.RELAY_IP:
            return RelayConfig(
                name="default",
                ip=settings.RELAY_IP,
                ssh_user=settings.RELAY_SSH_USER,
                ssh_port=settings.RELAY_SSH_PORT,
                lport=settings.RELAY_LPORT,
            )

        return None

    def list_relays(self) -> list[RelayConfig]:
        """List all configured relays (multi + legacy fallback)."""
        relays = list(self._configs)
        if not relays and settings.RELAY_IP:
            relays.append(RelayConfig(
                name="default",
                ip=settings.RELAY_IP,
                ssh_user=settings.RELAY_SSH_USER,
                ssh_port=settings.RELAY_SSH_PORT,
                lport=settings.RELAY_LPORT,
            ))
        return relays
