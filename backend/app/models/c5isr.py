# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

from pydantic import BaseModel

from .enums import C5ISRDomain, C5ISRDomainStatus


class C5ISRStatus(BaseModel):
    id: str
    operation_id: str
    domain: C5ISRDomain | str
    status: C5ISRDomainStatus | str
    health_pct: float                   # 0-100
    detail: str = ""
    # Structured metrics for frontend tactical display
    numerator: int | None = None        # e.g. alive_agents=2
    denominator: int | None = None      # e.g. total_agents=3
    metric_label: str = ""              # e.g. "agents alive"
