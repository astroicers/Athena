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

"""OSINT domain models."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class SubdomainInfo(BaseModel):
    subdomain: str
    resolved_ips: list[str]
    source: str  # "crtsh" | "subfinder" | "dns_bruteforce"


class OSINTResult(BaseModel):
    domain: str
    operation_id: str
    subdomains_found: int
    ips_resolved: int
    targets_created: int
    facts_written: int
    scan_duration_sec: float
    sources_used: list[str]
    subdomains: list[SubdomainInfo] = []


class OSINTDiscoverQueued(BaseModel):
    status: Literal["queued"] = "queued"
    operation_id: str
    domain: str
