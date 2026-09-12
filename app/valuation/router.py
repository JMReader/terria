from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas import PolygonGeometry
from app.store import FieldNotFound, get_field_store
from app.valuation.engine import run_land_valuation_projection
from app.valuation.schemas import (
    FieldValuationRequest,
    ValuationResponse,
    ValuationSimulateRequest,
)

router = APIRouter()
field_store = get_field_store()


def _field_not_found(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "FIELD_NOT_FOUND",
            "message": "The field was not found",
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


@router.post(
    "/v1/fields/{field_id}/valuations/5yr",
    response_model=ValuationResponse,
    summary="Project land value at 5 years for an existing field",
    tags=["Valuation"],
)
def project_field_valuation(
    field_id: UUID,
    payload: FieldValuationRequest,
    request: Request,
) -> ValuationResponse:
    """Proyecta el valor de la tierra a 5 años directamente sobre un campo persistido en el store.

    Hereda automáticamente el polígono perimetral, la superficie en hectáreas y la ubicación física del lote.
    """
    try:
        stored = field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None

    field = stored.value
    return run_land_valuation_projection(
        geometry_data=field.boundary,
        lot_name=field.name,
        projection_years=payload.projection_years,
        field_id=field_id,
        surface_ha=field.area_hectares,
        include_audit=payload.include_audit,
    )


@router.post(
    "/v1/valuations/5yr",
    response_model=ValuationResponse,
    summary="Project land value at 5 years with ad-hoc geometry",
    tags=["Valuation"],
)
def project_standalone_valuation(
    payload: ValuationSimulateRequest,
) -> ValuationResponse:
    """Proyecta el valor de la tierra a 5 años enviando directamente un polígono GeoJSON o coordenadas."""
    if payload.boundary:
        geom_input: Any = payload.boundary
    elif payload.coordinates:
        geom_input = {
            "type": "Polygon",
            "coordinates": [payload.coordinates],
        }
    elif payload.centroid_lat is not None and payload.centroid_lon is not None:
        geom_input = {
            "type": "Point",
            "coordinates": [payload.centroid_lon, payload.centroid_lat],
        }
    else:
        # Polígono por defecto (Lote Marcos Juárez / Córdoba)
        geom_input = PolygonGeometry(
            type="Polygon",
            coordinates=[
                [
                    [-62.11, -32.70],
                    [-62.09, -32.70],
                    [-62.09, -32.69],
                    [-62.11, -32.69],
                    [-62.11, -32.70],
                ]
            ],
        )

    return run_land_valuation_projection(
        geometry_data=geom_input,
        lot_name=payload.name,
        projection_years=payload.projection_years,
        surface_ha=payload.area_hectares,
        include_audit=payload.include_audit,
    )


@router.get(
    "/v1/valuations/drivers",
    summary="Get description and formulas of the 3 valuation drivers",
    tags=["Valuation"],
)
def get_valuation_drivers_guide() -> dict[str, Any]:
    """Retorna la metodología y reglas de negocio de los 3 multiplicadores de apreciación de la tierra."""
    return {
        "title": "Metodología del Proyector de Valor de Tierra a 5 Años (TERRIA v3.0)",
        "formula": "Projected_Value = V0 * M_log * M_agro * M_mkt",
        "drivers": {
            "V0_base_value": {
                "description": "Valor base actual del suelo rural en USD/ha al inicio de la valuación.",
                "source": "IDECOR WFS (Córdoba) / Modelo Dinámico Edafológico-Logístico (INTA / BCR).",
            },
            "M_log_logistic": {
                "description": "Resiliencia hídrica por cota de napa freática (amortiguador estival), riego pivote y conectividad vial.",
                "rule": "Napa freática óptima (1.5m-2.5m = aporte capilar 150-250 mm = +3.5% a +6.5%), riego (+8%), rutas pavimentadas.",
                "source": "Red de Monitoreo Freático INTA / IGN / OSM Vialidad.",
            },
            "M_agro_agronomic": {
                "description": "Salud de suelo, rotación balanceada y estabilidad de biomasa satelital Sentinel-2 (NDVI).",
                "rule": "Serie histórica SAGyP 15a modulada por salud edafológica con elasticidad de renta agraria de Ricardo-Thünen (0.52).",
                "source": "SAGyP Estimaciones Agrícolas / Copernicus Sentinel-2.",
            },
            "M_mkt_market": {
                "description": "Ciclo de renta y capitalización rural en quintales de soja por hectárea.",
                "rule": "Valor locativo de referencia en qq soja/ha capitalizado a tasa CAIR/BCR (2.85% anual) con tasa compuesta realista en USD.",
                "source": "Cámara Argentina de Inmobiliarias Rurales (CAIR) / Bolsa de Comercio de Rosario (BCR) / BCCBA.",
            },
        },
    }
