from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.valuation.agronomic_trend import calculate_agronomic_multiplier
from app.valuation.idecor import fetch_base_land_value
from app.valuation.schemas import (
    DriversBreakdown,
    FinancialTotals,
    MarketDriver,
    ValuationData,
    ValuationResponse,
)
from app.valuation.vialidad import calculate_logistic_multiplier
from app.what_if.geometry import parse_geometry_input


def compute_valuation_content_hash(
    lot_info: dict[str, Any],
    drivers_data: dict[str, Any],
    totals_data: dict[str, Any],
) -> str:
    """Calcula el hash determinista SHA-256 de la valuación para certificación on-chain (Solana memo / cert.inputs)."""
    payload = {
        "schema_version": "0.1",
        "algorithm_version": "3.0.0",
        "lot": lot_info,
        "drivers": drivers_data,
        "totals": totals_data,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_land_valuation_projection(
    *,
    geometry_data: Any,
    lot_name: str = "Lote Valuación",
    projection_years: int = 5,
    field_id: UUID | None = None,
    surface_ha: float | None = None,
    include_audit: bool = True,
    allow_network: bool = True,
) -> ValuationResponse:
    """Ejecuta el pipeline completo de valuación y apreciación de la tierra a N años."""
    c_lat, c_lon, calc_surface_ha, bbox = parse_geometry_input(geometry_data)
    effective_surface_ha = surface_ha if (surface_ha is not None and surface_ha > 0) else calc_surface_ha

    current_year = 2026
    target_year = current_year + projection_years

    # 1. Valor base actual de la tierra (IDECOR / Matriz Regional)
    base_info = fetch_base_land_value(c_lat, c_lon, allow_network=allow_network)
    base_usd_ha = base_info["base_value_usd_ha"]

    # 2. Multiplicador logístico por cercanía a obras viales (Overpass OSM)
    logistic_driver = calculate_logistic_multiplier(c_lat, c_lon, allow_network=allow_network)

    # 3. Multiplicador agronómico tendencial (CAGR SAGyP a 15 años con factor 0.8)
    agronomic_driver = calculate_agronomic_multiplier(c_lat, c_lon, projection_years, allow_network=allow_network)

    # 4. Multiplicador macroeconómico de mercado (+2.0% anual compuesto)
    market_annual_rate = 2.0
    market_multiplier = round((1.0 + (market_annual_rate / 100.0)) ** projection_years, 4)
    market_impact_pct = round((market_multiplier - 1.0) * 100.0, 2)
    market_driver = MarketDriver(
        impact_percentage=market_impact_pct,
        multiplier=market_multiplier,
        annual_rate_pct=market_annual_rate,
        detail=f"Apreciación inmobiliaria histórica del activo rural en USD (+{market_annual_rate}% anual compuesto a {projection_years} años).",
    )

    # 5. Ecuación integral de valor
    # Projected_Value = V0 * M_log * M_agro * M_mkt
    projected_usd_ha = round(
        base_usd_ha * logistic_driver.multiplier * agronomic_driver.multiplier * market_driver.multiplier,
        2,
    )
    total_appreciation_pct = round(((projected_usd_ha - base_usd_ha) / base_usd_ha) * 100.0, 1)

    # Totales financieros para la superficie total del lote
    total_base_usd = round(base_usd_ha * effective_surface_ha, 2)
    total_projected_usd = round(projected_usd_ha * effective_surface_ha, 2)
    total_capital_gain_usd = round(total_projected_usd - total_base_usd, 2)

    financial_totals = FinancialTotals(
        surface_ha=effective_surface_ha,
        total_base_value_usd=total_base_usd,
        total_projected_value_usd=total_projected_usd,
        total_capital_gain_usd=total_capital_gain_usd,
    )

    drivers_breakdown = DriversBreakdown(
        logistic_improvement=logistic_driver,
        agronomic_trend=agronomic_driver,
        market_appreciation=market_driver,
    )

    # Enlaces de auditoría externa
    audit_urls = None
    if include_audit:
        audit_urls = {
            "idecor_mapas_cordoba": base_info.get("audit_url", "https://mapascordoba.gob.ar/#/mapas/tierra-rural"),
            "osm_overpass_vialidad": f"https://overpass-turbo.eu/?lat={c_lat}&lon={c_lon}&zoom=11",
            "sagyp_estimaciones_oficiales": "https://datos.magyp.gob.ar/dataset/estimaciones-agricolas",
            "cair_inmobiliarias_rurales": "https://cairural.com.ar/informes-sectoriales/",
        }

    # Hash criptográfico para anclaje on-chain
    lot_summary = {
        "name": lot_name,
        "centroid": [c_lat, c_lon],
        "surface_ha": effective_surface_ha,
        "department": base_info.get("department"),
        "province": base_info.get("province"),
    }
    drivers_summary = {
        "base_usd_ha": base_usd_ha,
        "logistic_multiplier": logistic_driver.multiplier,
        "agronomic_multiplier": agronomic_driver.multiplier,
        "market_multiplier": market_driver.multiplier,
        "projected_usd_ha": projected_usd_ha,
    }
    totals_summary = {
        "total_base_usd": total_base_usd,
        "total_projected_usd": total_projected_usd,
        "total_capital_gain_usd": total_capital_gain_usd,
    }
    content_hash = compute_valuation_content_hash(lot_summary, drivers_summary, totals_summary)

    valuation_data = ValuationData(
        current_year=current_year,
        target_year=target_year,
        projection_years=projection_years,
        base_value_usd_ha=base_usd_ha,
        projected_value_usd_ha=projected_usd_ha,
        total_appreciation_percentage=total_appreciation_pct,
        drivers_breakdown=drivers_breakdown,
        financial_totals=financial_totals,
        content_hash=content_hash,
        audit_urls=audit_urls,
    )

    return ValuationResponse(
        status="success",
        schema_version="0.1",
        algorithm_version="3.0.0",
        field_id=field_id,
        lot_name=lot_name,
        valuation=valuation_data,
    )
