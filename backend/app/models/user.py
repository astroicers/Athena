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


class User(BaseModel):
    id: str
    callsign: str
    role: str = "Commander"
    created_at: datetime
