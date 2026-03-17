# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Router package — re-exports all router modules for convenient mounting."""

from . import (
    admin,
    agents,
    c5isr,
    engagements,
    facts,
    health,
    logs,
    missions,
    ooda,
    operations,
    recon,
    recommendations,
    reports,
    targets,
    techniques,
    terminal,
    tools,
    ws,
)

__all__ = [
    "admin",
    "agents",
    "c5isr",
    "engagements",
    "facts",
    "health",
    "logs",
    "missions",
    "ooda",
    "operations",
    "recon",
    "recommendations",
    "reports",
    "targets",
    "techniques",
    "terminal",
    "tools",
    "ws",
]
