"""Configuration loader — CLI flags > env vars > ~/.athena/config.toml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[import-untyped,no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

_CONFIG_DIR = Path.home() / ".athena"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"


@dataclass
class CLIConfig:
    base_url: str = "http://localhost:58000"
    ws_url: str = ""  # derived from base_url if empty
    json_output: bool = False
    no_color: bool = False
    default_op_id: str | None = None

    def __post_init__(self) -> None:
        if not self.ws_url:
            self.ws_url = self.base_url.replace("https://", "wss://").replace(
                "http://", "ws://"
            )


def load_config(
    *,
    base_url: str | None = None,
    json_output: bool = False,
    no_color: bool = False,
) -> CLIConfig:
    """Load config with priority: CLI flags > env vars > config file."""
    file_cfg: dict = {}
    if _CONFIG_FILE.exists() and tomllib is not None:
        with open(_CONFIG_FILE, "rb") as f:
            file_cfg = tomllib.load(f)

    return CLIConfig(
        base_url=(
            base_url
            or os.environ.get("ATHENA_BASE_URL")
            or file_cfg.get("base_url", "http://localhost:58000")
        ),
        ws_url=os.environ.get("ATHENA_WS_URL", file_cfg.get("ws_url", "")),
        json_output=json_output,
        no_color=no_color,
        default_op_id=(
            os.environ.get("ATHENA_DEFAULT_OP")
            or file_cfg.get("default_op_id")
        ),
    )


# Singleton — set once in main.py callback, read everywhere.
_cfg: CLIConfig | None = None


def set_global_config(cfg: CLIConfig) -> None:
    global _cfg
    _cfg = cfg


def get_config() -> CLIConfig:
    if _cfg is None:
        return CLIConfig()
    return _cfg
