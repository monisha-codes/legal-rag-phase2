from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Module 12 Response Formatter"
    app_version: str = "1.0.0"

    default_disclaimer: str = (
        "Disclaimer: This response is generated from retrieved legal sources and "
        "is intended for informational assistance only. It is not a substitute "
        "for professional legal advice."
    )

    free_tier_word_limit: int = 400
    paid_tier_word_limit: int = 0
    pro_tier_word_limit: int = 0
    enterprise_tier_word_limit: int = 0

    enable_cache_write: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()