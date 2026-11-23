from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    llm_provider: str = "gemini"  # gemini | mock
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash"  # tried when the main model keeps failing
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
