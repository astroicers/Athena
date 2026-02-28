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

"""Pydantic models for the ReconEngine scan results."""

from pydantic import BaseModel


class ServiceInfo(BaseModel):
    port: int
    protocol: str        # "tcp" | "udp"
    service: str         # e.g. "ssh"
    version: str         # e.g. "OpenSSH 7.4"
    state: str           # "open"


class ReconResult(BaseModel):
    target_id: str
    operation_id: str
    ip_address: str
    os_guess: str | None
    services: list[ServiceInfo]
    facts_written: int
    scan_duration_sec: float
    raw_xml: str | None  # nullable — omit in mock mode


class InitialAccessResult(BaseModel):
    success: bool
    method: str           # "ssh_credential" | "none"
    credential: str | None  # "user:pass" if found
    agent_deployed: bool
    error: str | None


class ReconScanResult(BaseModel):
    scan_id: str
    status: str           # "completed" | "failed"
    target_id: str
    operation_id: str
    ip_address: str
    os_guess: str | None
    services_found: int
    facts_written: int
    initial_access: InitialAccessResult
    scan_duration_sec: float
