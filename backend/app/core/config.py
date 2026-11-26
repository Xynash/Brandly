from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    llm_provider: str = "gemini"  # gemini | mock
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.5-flash"  # tried when the main model keeps failing
    gemini_timeout_seconds: int = 25  # per model call
    generate_rate_limit_per_minute: int = 10  # per agency
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"  # comma separated
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
