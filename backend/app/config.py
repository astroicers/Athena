from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite:///backend/data/athena.db"
    CALDERA_URL: str = "http://localhost:8888"
    CALDERA_API_KEY: str = ""
    MOCK_CALDERA: bool = True
    SHANNON_URL: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-opus-4-20250514"
    AUTOMATION_MODE: str = "semi_auto"
    RISK_THRESHOLD: str = "medium"
    LOG_LEVEL: str = "INFO"
    MOCK_LLM: bool = True


settings = Settings()
