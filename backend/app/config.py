# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # .../Athena


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///backend/data/athena.db"
    C2_ENGINE_URL: str = "http://localhost:8888"
    # External URL that deployed agents (on target machines) use to reach the C2 engine.
    # Must be reachable from the target network, e.g. http://192.168.0.18:58888
    # Defaults to C2_ENGINE_URL when not set.
    C2_AGENT_CALLBACK_URL: str = ""
    C2_ENGINE_API_KEY: str = ""
    MOCK_C2_ENGINE: bool = True
    # "ssh" | "persistent_ssh" | "c2" | "mock"
    EXECUTION_ENGINE: str = "ssh"
    PERSISTENT_SSH_SESSION_TIMEOUT_SEC: int = 300
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
    PERSISTENCE_ENABLED: bool = False
    WINRM_ENABLED: bool = False
    WINRM_TIMEOUT_SEC: int = 30
    # MCP integration (Phase 1)
    MCP_ENABLED: bool = False
    MCP_SERVERS_FILE: str = "mcp_servers.json"
    MCP_TOOL_TIMEOUT_SEC: int = 120
    MCP_RECONNECT_INTERVAL_SEC: int = 5
    MCP_MAX_RETRIES: int = 3


settings = Settings()
