# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""C5ISR and OODA domain schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import C5ISRDomainStatus


class C5ISRUpdate(BaseModel):
    status: C5ISRDomainStatus | None = None
    health_pct: float | None = None
    detail: str | None = None


class OODATimelineEntry(BaseModel):
    iteration_number: int
    phase: str
    summary: str
    timestamp: str
