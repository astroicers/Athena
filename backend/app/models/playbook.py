# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Playbook models for technique knowledge base."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlaybookCreate(BaseModel):
    mitre_id: str
    platform: str = "linux"
    command: str
    output_parser: str | None = None
    facts_traits: list[str] = []
    tags: list[str] = []


class PlaybookUpdate(BaseModel):
    command: str | None = None
    output_parser: str | None = None
    facts_traits: list[str] | None = None
    tags: list[str] | None = None


class Playbook(BaseModel):
    id: str
    mitre_id: str
    platform: str
    command: str
    output_parser: str | None
    facts_traits: list[str]
    source: str
    tags: list[str]
    created_at: datetime
