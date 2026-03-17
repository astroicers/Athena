# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""System-level schemas: health, logs, node summaries, facts."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.log_entry import LogEntry


class HealthStatus(BaseModel):
    status: str
    version: str
    services: dict


class PaginatedLogs(BaseModel):
    items: list[LogEntry]
    total: int
    page: int
    page_size: int


class NodeSummaryContent(BaseModel):
    attack_surface: str
    credential_chain: str
    lateral_movement: str
    persistence: str
    risk_assessment: str
    recommended_next: str


class NodeSummaryResponse(BaseModel):
    summary: NodeSummaryContent
    fact_count: int
    cached: bool
    generated_at: str
    model: str


class FactCreate(BaseModel):
    trait: str
    value: str
    category: str
    source_target_id: str | None = None
    source_technique_id: str | None = None
    score: int = 1
