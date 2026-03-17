# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Target management schemas."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class TargetCreate(BaseModel):
    hostname: str
    # Accepts IPv4, IPv6, or resolvable hostname/domain -- validated loosely to
    # allow any target that nmap can scan (IP, FQDN, CIDR notation, etc.)
    ip_address: str
    os: str | None = None
    role: str | None = None
    network_segment: str | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_target_address(cls, v: str) -> str:
        import ipaddress
        import re
        v = v.strip()
        if not v:
            raise ValueError("Target address must not be empty")
        # Accept IPv4 / IPv6
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        # Accept CIDR ranges (e.g. 192.168.1.0/24)
        try:
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            pass
        # Accept hostnames / FQDNs / simple domain names
        # Allow: letters, digits, hyphens, dots -- min 1 char
        hostname_re = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
            r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
        )
        if hostname_re.match(v):
            return v
        raise ValueError(
            f"{v!r} is not a valid IPv4 address, IPv6 address, CIDR range, or hostname"
        )


class TargetPatch(BaseModel):
    is_compromised: bool | None = None
    privilege_level: str | None = None   # "Root" | "User"
    access_status: str | None = None
    os: str | None = None
    role: str | None = None
    network_segment: str | None = None


class TargetSetActive(BaseModel):
    target_id: str  # empty string = deselect all


class TargetBatchCreate(BaseModel):
    entries: list[TargetCreate]
    role: str = "target"
    os: str | None = None
    network_segment: str | None = None


class BatchImportResult(BaseModel):
    created: list[str]            # created target IDs
    skipped_duplicates: list[str]  # duplicate IP addresses
    total_requested: int
    total_created: int


class TopologyNode(BaseModel):
    id: str
    label: str
    type: str = "host"  # "host" | "c2" | "agent"
    x: float | None = None
    y: float | None = None
    data: dict = {}


class TopologyEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    data: dict = {}


class TopologyData(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
