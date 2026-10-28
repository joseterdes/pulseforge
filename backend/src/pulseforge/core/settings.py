from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    supabase_url: str
    jwt_audience: str = "authenticated"
    tos_version: str = "v1"

    @field_validator("supabase_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
