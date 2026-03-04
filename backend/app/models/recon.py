# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Pydantic models for the ReconEngine scan results."""

from typing import Literal

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
    services: list[ServiceInfo] = []
    facts_written: int
    initial_access: InitialAccessResult
    scan_duration_sec: float


class ReconScanQueued(BaseModel):
    scan_id: str
    status: Literal["queued"] = "queued"
    target_id: str
    operation_id: str
