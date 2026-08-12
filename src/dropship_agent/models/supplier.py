from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SupplierProfile(BaseModel):
    """Normalized supplier record sourced from a marketplace supplier network."""

    model_config = ConfigDict(extra="forbid")

    supplier_id: str
    name: str
    platform: str = Field(..., description="e.g., 'aliexpress', 'cj_dropshipping'")
    shipping_latency_days_avg: float = Field(..., ge=0.0)
    shipping_latency_variance_days: float = Field(..., ge=0.0)
    stock_level: int = Field(..., ge=0)
    dispute_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of transactions disputed"
    )
    on_time_delivery_rate: float = Field(..., ge=0.0, le=1.0)
    years_active: float = Field(..., ge=0.0)


class RiskScoreMatrix(BaseModel):
    """Computed risk assessment for a supplier, produced by SupplierSourcingAgent."""

    model_config = ConfigDict(extra="forbid")

    supplier_id: str
    shipping_risk: float = Field(
        ..., ge=0.0, le=1.0, description="0 = reliable, 1 = high variance/slow"
    )
    stock_risk: float = Field(..., ge=0.0, le=1.0)
    dispute_risk: float = Field(..., ge=0.0, le=1.0)
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Weighted composite risk")
    recommendation: str = Field(..., description="'approve' | 'reject' | 'monitor'")
    rationale: str
