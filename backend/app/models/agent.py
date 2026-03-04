# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

from datetime import datetime

from pydantic import BaseModel

from .enums import AgentStatus


class Agent(BaseModel):
    id: str
    paw: str                            # "AGENT-7F3A"
    host_id: str                        # FK -> Target
    status: AgentStatus
    privilege: str                      # "SYSTEM"
    last_beacon: datetime | None = None
    beacon_interval_sec: int = 5
    platform: str                       # "windows"
    operation_id: str
