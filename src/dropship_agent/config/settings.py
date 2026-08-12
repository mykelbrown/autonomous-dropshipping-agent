from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central runtime configuration, populated from environment variables / .env.

    Fields are Optional so the app can boot without every integration configured;
    each client validates presence of the keys it specifically needs at call time.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM providers
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"
    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-1.5-flash"

    # Amazon live data
    rainforest_api_key: SecretStr | None = None

    # eBay Developer REST API
    ebay_app_id: str | None = None
    ebay_cert_id: str | None = None
    ebay_client_secret: SecretStr | None = None
    ebay_environment: str = "production"

    # Generic scraping proxies
    brightdata_api_key: SecretStr | None = None
    scrapingbee_api_key: SecretStr | None = None

    # Storefront targets
    shopify_store_domain: str | None = None
    shopify_admin_api_token: SecretStr | None = None
    shopify_api_version: str = "2024-07"

    # Integration test fixtures
    test_amazon_asin: str | None = None
    test_ebay_item_id: str | None = None

    # Runtime
    log_level: str = "INFO"
    log_dir: Path = Path("logs")

    def require(self, value: str | SecretStr | None, name: str) -> str:
        """Fetch a required config value or raise a clear, actionable error."""
        if value is None:
            raise RuntimeError(
                f"Missing required configuration '{name}'. Set it in your .env file "
                f"(see .env.example)."
            )
        return value.get_secret_value() if isinstance(value, SecretStr) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
