# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""OSINT domain models."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class SubdomainInfo(BaseModel):
    subdomain: str
    resolved_ips: list[str]
    source: str  # "crtsh" | "subfinder" | "dns_bruteforce"


class OSINTResult(BaseModel):
    domain: str
    operation_id: str
    subdomains_found: int
    ips_resolved: int
    targets_created: int
    facts_written: int
    scan_duration_sec: float
    sources_used: list[str]
    subdomains: list[SubdomainInfo] = []


class OSINTDiscoverQueued(BaseModel):
    status: Literal["queued"] = "queued"
    operation_id: str
    domain: str
