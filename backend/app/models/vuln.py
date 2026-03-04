# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]


"""Vulnerability domain models."""

from __future__ import annotations
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
