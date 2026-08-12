from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dropship_agent.models.listing import ListingDraft


class StorefrontConnector(ABC):
    """Abstract API interaction layer for pushing/updating listings on a storefront."""

    @abstractmethod
    async def upsert_listing(self, listing: ListingDraft) -> dict[str, Any]:
        """Create the listing if new, otherwise update it. Returns the platform response."""

    @abstractmethod
    async def update_price(self, external_id: str, new_price: float) -> dict[str, Any]:
        """Push a price update for an existing listing."""

    @abstractmethod
    async def update_inventory(self, external_id: str, quantity: int) -> dict[str, Any]:
        """Push a stock-level update for an existing listing."""
