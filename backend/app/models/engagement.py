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
