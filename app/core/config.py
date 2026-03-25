from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./gt7_advisor.db"

    # PlayStation
    ps_ip: str = "192.168.1.100"

    # LLM
    llm_provider: str = "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-6"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Community catalog
    gt7_cars_csv_url: str = "https://ddm999.github.io/gt7info/data/db/cars.csv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
