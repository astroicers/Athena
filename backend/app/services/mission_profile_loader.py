# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Load mission profile definitions from YAML config.

Usage:
    from app.services.mission_profile_loader import get_profile, NOISE_RANKS

    profile = get_profile("CO")
    if NOISE_RANKS[technique.noise_level] > NOISE_RANKS[profile["max_noise"]]:
        # technique is too noisy for this mission
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "mission_profiles.yaml"

# Noise ranking: lower = quieter.  "all" means no limit.
NOISE_RANKS: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "all": 99,
}

VALID_PROFILE_CODES = ("SR", "CO", "SP", "FA")


@lru_cache(maxsize=1)
def _load_profiles() -> dict[str, dict[str, Any]]:
    """Parse and cache all profiles from the YAML file."""
    with open(_PROFILES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    profiles = data.get("profiles", {})
    logger.info("Loaded %d mission profiles from %s", len(profiles), _PROFILES_PATH.name)
    return profiles


def get_profile(code: str) -> dict[str, Any]:
    """Return the profile dict for a mission code (SR/CO/SP/FA).

    Falls back to SP if the code is unknown.
    """
    profiles = _load_profiles()
    if code not in profiles:
        logger.warning("Unknown mission profile '%s', falling back to SP", code)
        code = "SP"
    return profiles[code]


def get_all_profiles() -> dict[str, dict[str, Any]]:
    """Return all profile definitions."""
    return _load_profiles()


def noise_allowed(mission_code: str, technique_noise: str) -> bool:
    """Return True if the technique noise is within the mission's limit."""
    profile = get_profile(mission_code)
    max_noise = profile.get("max_noise", "high")
    return NOISE_RANKS.get(technique_noise, 2) <= NOISE_RANKS.get(max_noise, 3)
