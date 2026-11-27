from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    auth_mode: Literal["password", "development"] = "password"
    llm_provider: Literal["gemini", "openai", "anthropic", "mock"] = "gemini"
    provider_key_encryption_key: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.5-flash"  # tried when the main model keeps failing
    llm_timeout_seconds: int = 30
    gemini_timeout_seconds: int = 25  # per model call
    generate_rate_limit_per_minute: int = 10  # per agency
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"  # comma separated
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
