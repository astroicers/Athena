# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Operational constraint models for C5ISR reverse influence on OODA."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConstraintWarning(BaseModel):
    """Soft constraint: advisory message for the commander."""
    domain: str
    health_pct: float
    message: str


class ConstraintLimit(BaseModel):
    """Hard constraint: enforced limit on OODA behavior."""
    domain: str
    health_pct: float
    rule: str
    effect: dict = Field(default_factory=dict)


class OperationalConstraints(BaseModel):
    """Aggregate constraints derived from C5ISR health + OPSEC state.

    Produced by constraint_engine.evaluate() at the start of each OODA cycle.
    Consumed by orient_engine, decision_engine, engine_router, agent_swarm.
    """
    warnings: list[ConstraintWarning] = Field(default_factory=list)
    hard_limits: list[ConstraintLimit] = Field(default_factory=list)
    orient_max_options: int = 3
    min_confidence_override: float | None = None
    max_parallel_override: int | None = None
    blocked_targets: list[str] = Field(default_factory=list)
    forced_mode: str | None = None  # "recovery" | "recon_first" | None
    noise_budget_remaining: int = 50
    active_overrides: list[str] = Field(default_factory=list)

    @property
    def has_hard_limits(self) -> bool:
        return len(self.hard_limits) > 0

    @property
    def is_recovery_mode(self) -> bool:
        return self.forced_mode == "recovery"

    @property
    def is_recon_first(self) -> bool:
        return self.forced_mode == "recon_first"
