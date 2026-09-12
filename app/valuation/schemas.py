from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas import PolygonGeometry, StrictModel


class FieldValuationRequest(StrictModel):
    """Solicitud de proyección de valor para un campo existente en el store."""
    projection_years: int = Field(
        5, ge=1, le=20, description="Horizonte de proyección en años (1 a 20)"
    )
    include_audit: bool = Field(
        True, description="Incluir deep links y trazabilidad pública de auditoría"
    )


class ValuationSimulateRequest(StrictModel):
    """Solicitud de proyección de valor standalone con geometría ad-hoc."""
    name: str = Field("Lote Valuación", max_length=120)
    boundary: PolygonGeometry | None = None
    coordinates: list[list[float]] | None = None
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    area_hectares: float | None = None
    projection_years: int = Field(5, ge=1, le=20)
    include_audit: bool = Field(True)


class LogisticDriver(StrictModel):
    impact_percentage: float = Field(..., description="Apreciación porcentual por infraestructura vial (%)")
    multiplier: float = Field(..., description="Factor multiplicador logístico (M_log)")
    distance_to_current_paved_km: float = Field(..., description="Distancia actual al asfalto más cercano (km)")
    distance_to_future_paved_km: float = Field(..., description="Distancia futura a la nueva traza en obra (km)")
    distance_saved_km: float = Field(..., description="Reducción neta de distancia logística (km)")
    detail: str = Field(..., description="Detalle de la obra vial detectada")


class AgronomicDriver(StrictModel):
    impact_percentage: float = Field(..., description="Apreciación porcentual por mejora agronómica (%)")
    multiplier: float = Field(..., description="Factor multiplicador agronómico (M_agro)")
    cagr_annual_pct: float = Field(..., description="Tasa de Crecimiento Anual Compuesto de rinde (%)")
    detail: str = Field(..., description="Detalle de la serie histórica departamental SAGyP")


class MarketDriver(StrictModel):
    impact_percentage: float = Field(..., description="Apreciación porcentual de mercado del activo (%)")
    multiplier: float = Field(..., description="Factor multiplicador de mercado (M_mkt)")
    annual_rate_pct: float = Field(..., description="Tasa anual histórica de apreciación inmobiliaria en USD (%)")
    detail: str = Field(..., description="Fundamentación macroeconómica")


class DriversBreakdown(StrictModel):
    logistic_improvement: LogisticDriver
    agronomic_trend: AgronomicDriver
    market_appreciation: MarketDriver


class FinancialTotals(StrictModel):
    surface_ha: float = Field(..., description="Superficie total evaluada (hectáreas)")
    total_base_value_usd: float = Field(..., description="Valor base total del lote hoy (USD)")
    total_projected_value_usd: float = Field(..., description="Valor proyectado total del lote a futuro (USD)")
    total_capital_gain_usd: float = Field(..., description="Ganancia de capital neta esperada en el lote (USD)")


class ValuationData(StrictModel):
    current_year: int = Field(2026, description="Año base de inicio de la valuación")
    target_year: int = Field(2031, description="Año horizonte de reventa proyectado")
    projection_years: int = Field(5, description="Años proyectados")
    base_value_usd_ha: float = Field(..., description="Valor base actual de la tierra (USD/ha)")
    projected_value_usd_ha: float = Field(..., description="Valor proyectado de la tierra (USD/ha)")
    total_appreciation_percentage: float = Field(..., description="Retorno porcentual pasivo estimado / ROI (%)")
    drivers_breakdown: DriversBreakdown
    financial_totals: FinancialTotals
    content_hash: str = Field(..., description="Hash determinista SHA-256 para certificación on-chain")
    audit_urls: dict[str, str] | None = None


class ValuationResponse(StrictModel):
    status: Literal["success"] = "success"
    schema_version: str = "0.1"
    algorithm_version: str = "3.0.0"
    field_id: UUID | None = None
    lot_name: str
    valuation: ValuationData
