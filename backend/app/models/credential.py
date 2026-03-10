# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Credential models for the credential graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Credential(BaseModel):
    """A harvested credential."""
    id: str = ""
    operation_id: str
    username: str | None = None
    secret_type: str  # cleartext, ntlm_hash, ssh_key, kerberos_tgt, token
    secret_value: str = ""  # never exposed in API responses
    domain: str | None = None
    source_target_id: str | None = None
    source_technique_id: str | None = None
    valid_until: datetime | None = None
    tested_targets: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None


class CredentialGraphNode(BaseModel):
    """Node in the credential reuse graph."""
    id: str
    label: str
    node_type: str  # "credential" | "target" | "user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CredentialGraphEdge(BaseModel):
    """Edge in the credential reuse graph."""
    source: str
    target: str
    relation: str  # "harvested_from" | "tested_on" | "valid_on"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CredentialGraph(BaseModel):
    """Full credential reuse graph for an operation."""
    operation_id: str
    nodes: list[CredentialGraphNode] = Field(default_factory=list)
    edges: list[CredentialGraphEdge] = Field(default_factory=list)
