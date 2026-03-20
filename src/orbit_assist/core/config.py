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

    jobs_limit: int = 50
    jobs_occupation_field: str = "apaJ_2ja_LuF"
    jobs_occupation_group: str = "DJh5_yyF_hEM"
    jobs_municipality: str = "oYPt_yRA_Smm"

    google_credentials_path: str = "credentials.json"
    google_token_path: str = "token.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
