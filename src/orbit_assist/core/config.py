from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_title: str = "Orbit-Assist API"
    app_version: str = "0.1.0"

    database_url: str = "postgresql://postgres:password@localhost:5432/mydb"

    gemini_api_key: str

    base_api_url: str
    jobs_api_url: str

    jobs_limit: int = 20
    jobs_occupation_field: str = "apaJ_2ja_LuF"
    jobs_municipality: str = "oYPt_yRA_Smm"


@lru_cache
def get_settings() -> Settings:
    return Settings()
