# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

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


class PlaybookBulkCreate(BaseModel):
    playbooks: list[PlaybookCreate]


class PlaybookBulkResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


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
