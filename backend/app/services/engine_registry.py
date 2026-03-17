# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Engine Registry — maps engine name strings to BaseEngineClient instances.

Engines are registered at application startup (main.py lifespan).
EngineRouter can query the registry for discovery; direct constructor
injection is still used for primary dispatch.

Usage:
    # At startup:
    engine_registry.register("c2", C2EngineClient(...))
    engine_registry.register("metasploit", MetasploitEngineAdapter())

    # Discovery:
    engines = engine_registry.list_engines()

    # Testing — override a specific engine:
    engine_registry.register("c2", FakeC2Client())
"""
from __future__ import annotations

import logging

from app.clients import BaseEngineClient

logger = logging.getLogger(__name__)
_registry: dict[str, BaseEngineClient] = {}


def register(name: str, client: BaseEngineClient) -> None:
    """Register an engine by name. Last-write-wins (supports test overrides)."""
    _registry[name] = client
    logger.debug(
        "engine_registry: registered '%s' (%s)", name, type(client).__name__
    )


def get(name: str) -> BaseEngineClient | None:
    """Return registered client for engine name, or None if not registered."""
    return _registry.get(name)


def list_engines() -> list[str]:
    """Return names of all currently registered engines."""
    return list(_registry.keys())


def clear() -> None:
    """Clear all registrations. Intended for use in tests only."""
    _registry.clear()
