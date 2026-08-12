from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SEOMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str = Field(..., max_length=140)
    meta_description: str = Field(..., max_length=320)
    keywords: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)


class PricingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_cost: float = Field(..., ge=0.0, description="Supplier unit cost")
    competitor_price_floor: float = Field(..., ge=0.0)
    competitor_price_ceiling: float = Field(..., ge=0.0)
    recommended_price: float = Field(..., ge=0.0)
    margin_pct: float = Field(
        ..., description="(recommended_price - base_cost) / recommended_price"
    )


class ListingDraft(BaseModel):
    """Final generated listing, ready for storefront sync."""

    model_config = ConfigDict(extra="forbid")

    source_external_id: str
    title: str
    description_html: str
    seo: SEOMetadata
    pricing: PricingModel
    images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
