from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fanora API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "sqlite:///./fanora.db"
    monad_rpc_url: str = "https://testnet-rpc.monad.xyz"
    monad_chain_id: int = 10143
    badge_contract_address: str = ""
    operator_private_key: str = ""

    openai_api_key: str = ""
    openai_model: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

