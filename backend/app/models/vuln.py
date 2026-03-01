# Copyright 2026 Athena Contributors
# Licensed under the Apache License, Version 2.0

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
