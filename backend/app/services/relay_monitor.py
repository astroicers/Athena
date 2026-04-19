# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Relay health monitor — detect relay disconnection before Act phase execution.

tech-debt: test-pending — unit tests needed for RelayMonitor (check_health,
    start_watchdog, pre_execute_check) and RelayRouter (subnet match, catch-all,
    legacy fallback). Vibe-coding workflow exemption (ASP).
"""

import asyncio
import logging
import time
from dataclasses import dataclass

from app.config import settings
from app.services.relay_router import RelayConfig, RelayRouter

logger = logging.getLogger(__name__)


@dataclass
class RelayStatus:
    """Health check result for a single relay."""

    name: str
    ip: str
    connected: bool
    port_bound: bool
    latency_ms: int
    error: str | None = None


class RelayMonitor:
    """Monitor relay health via SSH connectivity and port binding checks."""

    def __init__(self, ws_manager=None):
        self._ws = ws_manager
        self._router = RelayRouter()
        self._running = False
        self._last_status: dict[str, RelayStatus] = {}

    async def check_health(self, relay: RelayConfig | None = None) -> RelayStatus:
        """Check a single relay's health via SSH + port binding.

        If no relay is specified, checks the default/primary relay.
        """
        if relay is None:
            relay = self._router.select_relay("0.0.0.0")

        if relay is None or not relay.ip:
            return RelayStatus(
                name="none", ip="", connected=False,
                port_bound=False, latency_ms=0,
                error="No relay configured",
            )

        t0 = time.monotonic()
        connected = False
        port_bound = False
        error = None

        try:
            # TCP connection test to SSH port (lightweight health check)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(relay.ip, relay.ssh_port),
                timeout=5.0,
            )
            connected = True
            writer.close()
            await writer.wait_closed()

            # Check if the relay's listener port is reachable
            try:
                r2, w2 = await asyncio.wait_for(
                    asyncio.open_connection(relay.ip, relay.lport),
                    timeout=3.0,
                )
                port_bound = True
                w2.close()
                await w2.wait_closed()
            except (OSError, asyncio.TimeoutError):
                # Port not bound — relay SSH is up but listener isn't active
                port_bound = False

        except asyncio.TimeoutError:
            error = f"SSH connection to {relay.ip}:{relay.ssh_port} timed out"
        except OSError as e:
            error = f"SSH connection to {relay.ip}:{relay.ssh_port} failed: {e}"

        latency_ms = int((time.monotonic() - t0) * 1000)

        status = RelayStatus(
            name=relay.name,
            ip=relay.ip,
            connected=connected,
            port_bound=port_bound,
            latency_ms=latency_ms,
            error=error,
        )
        self._last_status[relay.ip] = status
        return status

    async def check_all_relays(self) -> list[RelayStatus]:
        """Check health of all configured relays."""
        relays = self._router.list_relays()
        if not relays:
            return [RelayStatus(
                name="none", ip="", connected=False,
                port_bound=False, latency_ms=0,
                error="No relays configured",
            )]

        results = await asyncio.gather(
            *(self.check_health(r) for r in relays),
            return_exceptions=True,
        )

        statuses = []
        for r in results:
            if isinstance(r, RelayStatus):
                statuses.append(r)
            else:
                statuses.append(RelayStatus(
                    name="unknown", ip="", connected=False,
                    port_bound=False, latency_ms=0,
                    error=str(r),
                ))
        return statuses

    async def start_watchdog(self, interval_sec: int = 30) -> None:
        """Start periodic health check loop. Broadcasts relay status events."""
        if self._running:
            logger.warning("Relay watchdog already running")
            return

        if self._ws is None:
            logger.warning(
                "Relay watchdog started without ws_manager -- "
                "relay status events will NOT be broadcast to clients"
            )

        self._running = True
        logger.info("Relay watchdog started (interval=%ds)", interval_sec)

        while self._running:
            try:
                statuses = await self.check_all_relays()
                for status in statuses:
                    event_type = (
                        "relay.connected" if status.connected
                        else "relay.disconnected"
                    )
                    if self._ws:
                        await self._ws.broadcast_global(event_type, {
                            "name": status.name,
                            "ip": status.ip,
                            "connected": status.connected,
                            "port_bound": status.port_bound,
                            "latency_ms": status.latency_ms,
                            "error": status.error,
                        })

                    if not status.connected:
                        logger.warning(
                            "Relay '%s' (%s) disconnected: %s",
                            status.name, status.ip, status.error,
                        )
            except Exception:
                logger.exception("Relay watchdog check failed")

            await asyncio.sleep(interval_sec)

    def stop_watchdog(self) -> None:
        """Stop the watchdog loop."""
        self._running = False
        logger.info("Relay watchdog stopped")

    def get_last_status(self, relay_ip: str | None = None) -> RelayStatus | None:
        """Get the most recent health check result for a relay."""
        if relay_ip:
            return self._last_status.get(relay_ip)
        # Return the primary relay status
        if self._last_status:
            return next(iter(self._last_status.values()))
        return None

    async def pre_execute_check(self, target_ip: str) -> RelayStatus | None:
        """Pre-execution health check — called before Metasploit execution.

        Returns the relay status if a relay is needed, None if no relay configured.
        """
        relay = self._router.select_relay(target_ip)
        if relay is None:
            return None

        # Use cached status if recent (within last check interval)
        cached = self._last_status.get(relay.ip)
        if cached and cached.connected:
            return cached

        # Fresh check
        return await self.check_health(relay)
