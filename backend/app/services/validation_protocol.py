# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Shared validation protocol for all pre-action gatekeepers.

Three validators participate in the OODA pre-action chain:
  ScopeValidator     — pre-recon:   ROE geographic/temporal scope check
  ValidationEngine   — pre-decide:  technique technical feasibility
  ConstraintEngine   — pre-orient:  C5ISR domain health constraints

All implement PreActionValidator.check() and return a CheckResult.

Usage:
    from app.services.validation_protocol import run_chain, CheckResult
    passed, results = await run_chain([scope_v, tech_v], db, context)
    if not passed:
        raise ScopeViolationError(results[-1].reason)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import asyncpg


@dataclass(frozen=True)
class CheckResult:
    """Immutable result of a single pre-action validation check."""

    passed: bool
    reason: str
    confidence_delta: float = 0.0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, reason: str = "passed", delta: float = 0.0) -> "CheckResult":
        """Convenience constructor for a passing result."""
        return cls(passed=True, reason=reason, confidence_delta=delta)

    @classmethod
    def fail(cls, reason: str, delta: float = 0.0) -> "CheckResult":
        """Convenience constructor for a failing result."""
        return cls(passed=False, reason=reason, confidence_delta=delta)


class PreActionValidator(ABC):
    """Abstract interface for all pre-action validation gatekeepers.

    Each concrete validator documents the context keys it reads.
    """

    @abstractmethod
    async def check(self, db: asyncpg.Connection, context: dict) -> CheckResult:
        """Validate a pending action.

        Parameters
        ----------
        db:      Live database connection.
        context: Dict with at minimum 'operation_id'. Each validator
                 documents what additional keys it requires.

        Returns
        -------
        CheckResult — passed=True to allow, False to block.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name for logging."""
        return self.__class__.__name__


async def run_chain(
    validators: list[PreActionValidator],
    db: asyncpg.Connection,
    context: dict,
) -> tuple[bool, list[CheckResult]]:
    """Run validators in order; stop on first failure.

    Returns
    -------
    (all_passed: bool, results: list[CheckResult])
    """
    results: list[CheckResult] = []
    for validator in validators:
        result = await validator.check(db, context)
        results.append(result)
        if not result.passed:
            return False, results
    return True, results
