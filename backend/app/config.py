# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
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


settings = Settings()
