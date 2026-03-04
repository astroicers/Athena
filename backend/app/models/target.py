# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

from pydantic import BaseModel


class Target(BaseModel):
    id: str
    hostname: str                       # "DC-01"
    ip_address: str                     # "10.0.1.5"
    os: str | None = None               # "Windows Server 2019"
    role: str                           # "Domain Controller"
    network_segment: str | None = None  # "10.0.1.0/24"
    is_compromised: bool = False
    is_active: bool = False
    privilege_level: str | None = None  # "SYSTEM" | "Admin" | "User"
    operation_id: str
