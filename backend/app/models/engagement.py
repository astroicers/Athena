# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Engagement domain model."""

from __future__ import annotations
from pydantic import BaseModel


class Engagement(BaseModel):
    id: str
    operation_id: str
    client_name: str
    contact_email: str
    roe_document_path: str | None = None
    roe_signed_at: str | None = None
    scope_type: str = "whitelist"
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    start_time: str | None = None
    end_time: str | None = None
    emergency_contact: str | None = None
    status: str = "draft"
    created_at: str
