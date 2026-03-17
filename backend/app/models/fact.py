# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

from datetime import datetime

from pydantic import BaseModel

from .enums import FactCategory


class Fact(BaseModel):
    id: str
    trait: str                          # "host.user.name"
    value: str                          # "CORP\\Administrator"
    category: FactCategory | str
    source_technique_id: str | None = None
    source_target_id: str | None = None
    operation_id: str
    score: int = 1
    collected_at: datetime
