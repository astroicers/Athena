"""Defensive enum conversion utilities.

Prevents API crashes when DB contains enum values not yet in Python enums.
- safe_enum():         Read-side — returns raw string if value not in enum
- ensure_enum_value(): Write-side — validates before DB insert
"""

import logging
from enum import Enum
from typing import TypeVar

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)


def safe_enum(enum_cls: type[E], value: str | None, *, log_name: str = "") -> E | str | None:
    """Convert a DB value to an enum member, returning raw string if invalid.

    Use at the read boundary (DB row → Pydantic model) to prevent
    ValidationError crashes when the database contains values not in the enum.
    """
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        label = log_name or enum_cls.__name__
        logger.error(
            "Invalid %s value from DB: %r (valid: %s)",
            label,
            value,
            [m.value for m in enum_cls],
        )
        return value  # pass through as raw string


def ensure_enum_value(enum_cls: type[E], value: str, *, fallback_member: E | None = None) -> str:
    """Validate a value against an enum before DB write, returning .value string.

    Use at the write boundary (service → DB INSERT/UPDATE) to catch invalid
    values before they pollute the database.

    Raises ValueError if value is invalid and no fallback_member is given.
    """
    try:
        return enum_cls(value).value
    except ValueError:
        if fallback_member is not None:
            logger.warning(
                "Corrected invalid %s: %r -> %r",
                enum_cls.__name__,
                value,
                fallback_member.value,
            )
            return fallback_member.value
        raise
