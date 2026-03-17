# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com


"""Vulnerability domain models."""

from __future__ import annotations
from dataclasses import dataclass
from pydantic import BaseModel


class VulnFinding(BaseModel):
    cve_id: str
    service: str
    version: str
    cvss_score: float
    severity: str       # "critical" | "high" | "medium" | "low" | "info"
    description: str
    exploit_available: bool
    target_id: str
    operation_id: str


@dataclass
class ValidatedFinding:
    """Result of running a VulnFinding through the exploit validation pipeline."""

    cve_id: str                    # e.g. "CVE-2021-41773"
    service: str                   # e.g. "http"
    version: str                   # e.g. "Apache 2.4.49"
    cvss_score: float              # 0.0 - 10.0
    validation_status: str         # "confirmed" | "rejected" | "uncertain"
    validation_confidence: float   # 0.0 - 1.0
    validation_evidence: str       # human-readable evidence string
    exploit_available: bool        # True if public exploit found
    exploit_reference: str | None  # URL to PoC (Exploit-DB / GitHub)
    strategy_used: str             # e.g. "BackportCheckStrategy"
    target_id: str
    operation_id: str
