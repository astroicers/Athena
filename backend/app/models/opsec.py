# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""OPSEC monitoring models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OPSECEvent(BaseModel):
    """A single OPSEC event (e.g. auth failure, high noise, artifact)."""
    id: str = ""
    operation_id: str
    event_type: str
    severity: str = "warning"
    detail: dict[str, Any] = Field(default_factory=dict)
    target_id: str | None = None
    technique_id: str | None = None
    noise_points: int = 0
    created_at: datetime | None = None


class OPSECStatus(BaseModel):
    """Aggregate OPSEC status for an operation."""
    operation_id: str
    noise_score: float = 0.0
    dwell_time_score: float = 0.0
    exposure_count: int = 0
    artifact_footprint: float = 0.0
    detection_risk: float = 0.0
    noise_budget_total: int = 50
    noise_budget_used: int = 0
    noise_budget_remaining: int = 50
    recent_events: list[OPSECEvent] = Field(default_factory=list)


class ThreatLevel(BaseModel):
    """Computed threat level for an operation."""
    operation_id: str
    level: float = 0.0  # 0.0 - 1.0
    components: dict[str, float] = Field(default_factory=dict)
