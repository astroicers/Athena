# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Backward-compatibility shim.

New code should import from ``app.models.schemas`` or its sub-modules.
All 31 public classes are re-exported here so existing imports are unaffected.
"""

from app.models.schemas import *  # noqa: F401, F403
from app.models.schemas import (  # explicit re-export for type checkers / IDE
    AttackGraphEdge,
    AttackGraphNode,
    AttackGraphResponse,
    AttackGraphStats,
    AttackPathEntry,
    AttackPathResponse,
    BatchImportResult,
    C5ISRUpdate,
    EngagementCreate,
    FactCreate,
    HealthStatus,
    MissionStepCreate,
    MissionStepUpdate,
    NodeSummaryContent,
    NodeSummaryResponse,
    OODATimelineEntry,
    OperationCreate,
    OperationSummary,
    OperationUpdate,
    PaginatedLogs,
    SwarmBatchResponse,
    SwarmTaskSchema,
    TargetBatchCreate,
    TargetCreate,
    TargetPatch,
    TargetSetActive,
    TechniqueCreate,
    TechniqueWithStatus,
    TopologyData,
    TopologyEdge,
    TopologyNode,
)
