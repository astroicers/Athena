# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Domain schema subpackage.

Re-exports all public schema classes from the domain sub-modules so that
``from app.models.schemas import <AnyClass>`` works as expected.
"""

from app.models.schemas.attack import (
    AttackGraphEdge,
    AttackGraphNode,
    AttackGraphResponse,
    AttackGraphStats,
    AttackPathEntry,
    AttackPathResponse,
    SwarmBatchResponse,
    SwarmTaskSchema,
)
from app.models.schemas.c5isr import (
    C5ISRUpdate,
    OODATimelineEntry,
)
from app.models.schemas.missions import (
    EngagementCreate,
    MissionStepCreate,
    MissionStepUpdate,
)
from app.models.schemas.operations import (
    OperationCreate,
    OperationSummary,
    OperationUpdate,
)
from app.models.schemas.system import (
    FactCreate,
    HealthStatus,
    NodeSummaryContent,
    NodeSummaryResponse,
    PaginatedLogs,
)
from app.models.schemas.targets import (
    BatchImportResult,
    TargetBatchCreate,
    TargetCreate,
    TargetPatch,
    TargetSetActive,
    TopologyData,
    TopologyEdge,
    TopologyNode,
)
from app.models.schemas.techniques import (
    TechniqueCreate,
    TechniqueWithStatus,
)

__all__ = [
    # attack
    "AttackGraphEdge",
    "AttackGraphNode",
    "AttackGraphResponse",
    "AttackGraphStats",
    "AttackPathEntry",
    "AttackPathResponse",
    "SwarmBatchResponse",
    "SwarmTaskSchema",
    # c5isr
    "C5ISRUpdate",
    "OODATimelineEntry",
    # missions
    "EngagementCreate",
    "MissionStepCreate",
    "MissionStepUpdate",
    # operations
    "OperationCreate",
    "OperationSummary",
    "OperationUpdate",
    # system
    "FactCreate",
    "HealthStatus",
    "NodeSummaryContent",
    "NodeSummaryResponse",
    "PaginatedLogs",
    # targets
    "BatchImportResult",
    "TargetBatchCreate",
    "TargetCreate",
    "TargetPatch",
    "TargetSetActive",
    "TopologyData",
    "TopologyEdge",
    "TopologyNode",
    # techniques
    "TechniqueCreate",
    "TechniqueWithStatus",
]
