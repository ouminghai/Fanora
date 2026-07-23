"""Environment-driven application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Fanora settings shared by API, Agent, database, and adapters."""

    app_name: str = "Fanora API"
    version: str = "0.2.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    api_prefix: str = "/api/v1"
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    internal_api_key: str = ""
    auth_challenge_ttl_seconds: int = 300
    auth_session_ttl_seconds: int = 604800

    database_url: str = "sqlite+aiosqlite:///./fanora.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 60
    database_pool_recycle_seconds: int = 300
    database_connect_timeout_seconds: int = 60
    database_keepalive_idle_seconds: int = 30
    database_keepalive_interval_seconds: int = 10
    database_keepalive_count: int = 3
    auto_create_schema: bool = True
    migration_max_attempts: int = 5
    migration_retry_delay_seconds: float = 2

    checkpoint_database_url: str = ""
    checkpoint_pool_size: int = 5
    checkpoint_auto_setup: bool = False

    cache_url: str = ""
    cache_ttl_seconds: int = 60

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    openai_fallback_models: str = ""
    openai_image_model: str = "gpt-image-2"
    openai_image_size: str = "1024x1024"
    image_generation_timeout_seconds: float = 90.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1200
    llm_max_retries: int = 3
    llm_total_timeout_seconds: int = 60
    badge_draft_min_tokens: int = 500

    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    monad_rpc_url: str = "https://testnet-rpc.monad.xyz"
    monad_chain_id: int = 10143
    membership_treasury_address: str = ""
    membership_fee_wei: int = 1_000_000_000_000_000_000
    membership_min_confirmations: int = 1
    membership_payment_contract_address: str = ""
    membership_identity_contract_address: str = ""
    collectibles_contract_address: str = ""
    membership_identity_start_block: int = 0
    collectibles_start_block: int = 0
    chain_write_confirmations: int = 1
    chain_writes_enabled: bool = True
    chain_transaction_timeout_seconds: int = 90
    membership_treasury_manager_private_key: str = ""
    identity_minter_private_key: str = ""
    identity_level_manager_private_key: str = ""
    identity_uri_manager_private_key: str = ""
    collectible_type_manager_private_key: str = ""
    collectible_minter_private_key: str = ""
    collectible_uri_manager_private_key: str = ""
    pinata_jwt: str = ""
    pinata_api_url: str = "https://uploads.pinata.cloud/v3/files"
    pinata_gateway_url: str = "https://gateway.pinata.cloud/ipfs"
    pinata_timeout_seconds: float = 30.0
    pinata_max_retries: int = 3
    nft_max_image_bytes: int = 5_000_000
    nft_min_image_dimension: int = 256
    nft_max_image_dimension: int = 4096
    nft_publish_fee_fan_tokens: int = 100
    membership_card_fee_fan_tokens: int = 0
    nft_min_price_fan_tokens: int = 1
    nft_max_price_fan_tokens: int = 1_000_000
    nft_min_supply: int = 1
    nft_max_supply: int = 1_000
    fanora_issuer_name: str = "Fanora Protocol"

    log_level: str = "INFO"
    log_format: str = "console"
    rate_limit_default: str = "200 per hour"
    rate_limit_agent: str = "30 per minute"
    rate_limit_health: str = "60 per minute"
    rate_limit_auth: str = "20 per minute"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def llm_models(self) -> list[str]:
        values = [self.openai_model, *self.openai_fallback_models.split(",")]
        return list(dict.fromkeys(model.strip() for model in values if model.strip()))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key and self.llm_models)

    @property
    def postgres_connect_args(self) -> dict[str, int]:
        return {
            "connect_timeout": self.database_connect_timeout_seconds,
            "keepalives": 1,
            "keepalives_idle": self.database_keepalive_idle_seconds,
            "keepalives_interval": self.database_keepalive_interval_seconds,
            "keepalives_count": self.database_keepalive_count,
        }

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment == Environment.PRODUCTION and not self.internal_api_key:
            raise ValueError("INTERNAL_API_KEY is required in production until user authentication is implemented")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
