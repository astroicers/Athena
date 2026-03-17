# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Pydantic models for structured pentest report output (A.5)."""

from pydantic import BaseModel


class Finding(BaseModel):
    cve_id: str
    service: str
    version: str
    cvss_score: float
    severity: str  # critical | high | medium | low | info
    description: str
    exploit_available: bool
    target_id: str
    target_ip: str


class AttackStep(BaseModel):
    iteration_number: int
    phase: str
    observe_summary: str | None
    act_summary: str | None
    technique_id: str | None
    completed_at: str | None


class PentestReport(BaseModel):
    operation_id: str
    operation_name: str
    codename: str
    generated_at: str
    # Scope / Engagement
    client_name: str | None
    contact_email: str | None
    in_scope: list[str]
    out_of_scope: list[str]
    engagement_status: str | None
    # Executive Summary
    executive_summary: str
    # Metrics
    targets_discovered: int
    subdomains_found: int
    services_scanned: int
    vulnerabilities_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    # Findings (sorted by CVSS desc)
    findings: list[Finding]
    # Attack Narrative
    attack_steps: list[AttackStep]
    # Recommendations from OrientEngine
    orient_recommendations: list[dict]
    # MITRE ATT&CK coverage: tactic → list of technique IDs executed
    mitre_coverage: dict[str, list[str]]
