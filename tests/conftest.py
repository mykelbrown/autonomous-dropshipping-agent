from __future__ import annotations

import pytest

from dropship_agent.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)


def has_amazon_credentials(settings: Settings) -> bool:
    return bool(settings.rainforest_api_key and settings.test_amazon_asin)


def has_ebay_credentials(settings: Settings) -> bool:
    return bool(
        settings.ebay_app_id
        and settings.ebay_client_secret
        and settings.test_ebay_item_id
    )
