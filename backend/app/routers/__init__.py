"""Router package — re-exports all router modules for convenient mounting."""

from . import (
    agents,
    c5isr,
    facts,
    health,
    logs,
    missions,
    ooda,
    operations,
    recommendations,
    targets,
    techniques,
    ws,
)

__all__ = [
    "agents",
    "c5isr",
    "facts",
    "health",
    "logs",
    "missions",
    "ooda",
    "operations",
    "recommendations",
    "targets",
    "techniques",
    "ws",
]
