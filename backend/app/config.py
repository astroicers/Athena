# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # .../Athena


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://athena:athena_secret@localhost:55432/athena"
    C2_ENGINE_URL: str = "http://localhost:8888"
    # External URL that deployed agents (on target machines) use to reach the C2 engine.
    # Must be reachable from the target network, e.g. http://192.168.0.18:58888
    # Defaults to C2_ENGINE_URL when not set.
    C2_AGENT_CALLBACK_URL: str = ""
    C2_ENGINE_API_KEY: str = ""  # Set via .env or C2_ENGINE_API_KEY env var
    MOCK_C2_ENGINE: bool = True
    # "mcp_ssh" | "c2" | "mock"
    EXECUTION_ENGINE: str = "mcp_ssh"
    C2_MOCK_BEACON: bool = False  # True skips 30s beacon wait (only relevant when EXECUTION_ENGINE=c2)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_AUTH_TOKEN: str = ""
    OPENAI_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-opus-4-6"
    OPENAI_MODEL: str = "gpt-4-turbo"
    AUTOMATION_MODE: str = "semi_auto"
    RISK_THRESHOLD: str = "medium"
    LLM_BACKEND: str = "auto"  # "api_key" | "oauth" | "auto"
    LOG_LEVEL: str = "INFO"
    MOCK_LLM: bool = True
    OSINT_MAX_SUBDOMAINS: int = 500
    SUBFINDER_ENABLED: bool = True
    OSINT_REQUEST_TIMEOUT_SEC: int = 30
    NVD_API_KEY: str = ""
    NVD_CACHE_TTL_HOURS: int = 24
    VULN_LOOKUP_ENABLED: bool = True
    OODA_LOOP_INTERVAL_SEC: int = 30
    MSF_RPC_HOST: str = "127.0.0.1"
    MSF_RPC_PORT: int = 55553
    MSF_RPC_USER: str = "msf"
    MSF_RPC_PASSWORD: str = ""
    MSF_RPC_SSL: bool = False
    MOCK_METASPLOIT: bool = True
    # SPEC-053: Maximum time (seconds) to wait for a new Metasploit session
    # after an exploit is executed. Previously hard-coded to 30s in
    # metasploit_client._run_exploit. Configurable 10-300s range.
    METASPLOIT_SESSION_WAIT_SEC: int = 60
    PERSISTENCE_ENABLED: bool = False
    # MCP integration
    MCP_ENABLED: bool = True
    MCP_SERVERS_FILE: str = "mcp_servers.json"
    MCP_TOOL_TIMEOUT_SEC: int = 300
    MCP_RECONNECT_INTERVAL_SEC: int = 5
    MCP_MAX_RETRIES: int = 3
    MCP_TRANSPORT_MODE: str = "auto"  # "stdio" | "http" | "auto"
    CLAUDE_MODEL_OPUS: str = "claude-opus-4-6"
    CLAUDE_MODEL_SONNET: str = "claude-sonnet-4-20250514"
    CLAUDE_MODEL_HAIKU: str = "claude-haiku-4-5-20251001"
    NODE_SUMMARY_MODEL: str = "claude-sonnet-4-20250514"  # Legacy: superseded by TASK_MODEL_MAP["node_summary"]
    NMAP_SCAN_TIMEOUT_SEC: int = 60
    # Exploit validation (SPEC-028)
    EXPLOIT_VALIDATION_ENABLED: bool = True
    EXPLOIT_VALIDATION_SAFE_PROBE: bool = False
    EXPLOIT_VALIDATION_LLM_TRIAGE: bool = True
    EXPLOIT_VALIDATION_CONFIDENCE_THRESHOLD: float = 0.6
    EXPLOIT_VALIDATION_TIMEOUT_SEC: int = 30
    # AgentSwarm (ADR-027)
    MAX_PARALLEL_TASKS: int = 5           # Semaphore bound, range 1-20
    PARALLEL_TASK_TIMEOUT_SEC: int = 120  # Per-task timeout, range 10-600


settings = Settings()

def get_task_model_map() -> dict[str, str]:
    """Return task->model mapping, evaluated at call time for runtime override."""
    return {
        "orient_analysis":        settings.CLAUDE_MODEL_HAIKU,
        "fact_summary":           settings.CLAUDE_MODEL_HAIKU,
        "node_summary":           settings.CLAUDE_MODEL_HAIKU,
        "format_report":          settings.CLAUDE_MODEL_HAIKU,
        "classify_vulnerability": settings.CLAUDE_MODEL_HAIKU,
    }

# Backward-compat alias populated at startup
TASK_MODEL_MAP: dict[str, str] = {}

def _init_task_model_map() -> None:
    TASK_MODEL_MAP.clear()
    TASK_MODEL_MAP.update(get_task_model_map())
