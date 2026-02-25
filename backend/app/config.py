from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite:///backend/data/athena.db"
    CALDERA_URL: str = "http://localhost:8888"
    CALDERA_API_KEY: str = ""
    SHANNON_URL: str = ""
    PENTESTGPT_API_URL: str = "http://localhost:8080"
    PENTESTGPT_MODEL: str = "gpt-4"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AUTOMATION_MODE: str = "semi_auto"
    RISK_THRESHOLD: str = "medium"
    LOG_LEVEL: str = "INFO"
    MOCK_LLM: bool = True


settings = Settings()
