# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""ScopeValidator — enforces Rules of Engagement constraints on target selection."""

import ipaddress
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class ScopeCheckResult:
    in_scope: bool
    reason: str


class ScopeViolationError(Exception):
    """Raised when an action targets an out-of-scope asset."""


class ScopeValidator:
    """Validates whether a target address is within the engagement's defined scope.

    When no engagement record exists for an operation, all targets are considered
    in-scope (backward-compatible mode).
    """

    async def validate_target(
        self,
        db: asyncpg.Connection,
        operation_id: str,
        target_address: str,
    ) -> ScopeCheckResult:
        """Check whether target_address is within the engagement scope.

        Parameters
        ----------
        db:
            Database connection.
        operation_id:
            The operation to look up the engagement for.
        target_address:
            IPv4, IPv6, CIDR, or hostname/domain to validate.

        Returns
        -------
        ScopeCheckResult
            ``in_scope=True`` when allowed, ``in_scope=False`` otherwise.
        """
        # --- Fetch engagement record ---
        row = await db.fetchrow(
            "SELECT * FROM engagements WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 1",
            operation_id,
        )

        # No engagement → unrestricted (backward compatible)
        if row is None:
            return ScopeCheckResult(
                in_scope=True,
                reason="No engagement configured — unrestricted mode",
            )

        engagement = dict(row)

        # Engagement must be active
        if engagement["status"] != "active":
            return ScopeCheckResult(
                in_scope=False,
                reason=f"Engagement is not active (status={engagement['status']})",
            )

        # Time window check
        now = datetime.now(timezone.utc)
        if engagement.get("start_time") and now < engagement["start_time"]:
            return ScopeCheckResult(
                in_scope=False,
                reason=f"Outside engagement window (starts {engagement['start_time']})",
            )
        if engagement.get("end_time") and now > engagement["end_time"]:
            return ScopeCheckResult(
                in_scope=False,
                reason=f"Outside engagement window (ended {engagement['end_time']})",
            )

        # Parse scope lists
        in_scope_list: list[str] = json.loads(engagement.get("in_scope") or "[]")
        out_of_scope_list: list[str] = json.loads(engagement.get("out_of_scope") or "[]")

        # Out-of-scope takes priority
        if self._matches_any(target_address, out_of_scope_list):
            return ScopeCheckResult(
                in_scope=False,
                reason=f"{target_address!r} matches out-of-scope list",
            )

        # Must match in-scope
        if not in_scope_list:
            return ScopeCheckResult(
                in_scope=True,
                reason="Empty in-scope list — unrestricted",
            )

        if self._matches_any(target_address, in_scope_list):
            return ScopeCheckResult(
                in_scope=True,
                reason=f"{target_address!r} is within scope",
            )

        return ScopeCheckResult(
            in_scope=False,
            reason=f"{target_address!r} does not match any in-scope entry",
        )

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------

    def _matches_any(self, address: str, scope_list: list[str]) -> bool:
        """Return True if address matches any entry in scope_list."""
        for entry in scope_list:
            if self._matches_entry(address, entry):
                return True
        return False

    def _matches_entry(self, address: str, entry: str) -> bool:
        """Match address against a single scope entry.

        Supports:
        - Exact IPv4/IPv6 match ("192.168.1.5")
        - CIDR containment ("192.168.1.0/24")
        - Exact domain match ("example.com")
        - Wildcard subdomain match ("*.example.com")
        """
        entry = entry.strip()
        address = address.strip()

        # Try IP / CIDR matching first
        try:
            addr_obj = ipaddress.ip_address(address)
            # CIDR range?
            if "/" in entry:
                try:
                    network = ipaddress.ip_network(entry, strict=False)
                    return addr_obj in network
                except ValueError:
                    pass
            # Exact IP
            try:
                return addr_obj == ipaddress.ip_address(entry)
            except ValueError:
                pass
        except ValueError:
            pass  # address is a hostname, not an IP

        # Domain / hostname matching
        # Wildcard: "*.example.com" matches "mail.example.com" but not "example.com"
        if entry.startswith("*."):
            base_domain = entry[2:].lower()
            return address.lower().endswith("." + base_domain)

        # Exact domain match (case-insensitive)
        return address.lower() == entry.lower()
