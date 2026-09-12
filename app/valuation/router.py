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
                "source": "IDECOR WFS (Córdoba) / CAIR e INTA Relevamiento de Mercado (Buenos Aires, Santa Fe, Entre Ríos).",
            },
            "M_log_logistic": {
                "description": "Apreciación por nueva infraestructura vial en construcción o proyectada en un radio de 50 km.",
                "rule": "+3% de valor por cada 10 km que se reduzca la distancia al asfalto más cercano (piso 1.0, tope máximo +15%).",
                "source": "OpenStreetMap Overpass API (highway=construction o highway=proposed).",
            },
            "M_agro_agronomic": {
                "description": "Apreciación por ganancia genética y tecnológica de rendimientos agrícolas a 15 años.",
                "rule": "Tasa de Crecimiento Anual Compuesto (CAGR) trasladada al valor del suelo con factor 0.8.",
                "source": "SAGyP - Estimaciones Agrícolas Oficiales Departamentales (Soja y Maíz).",
            },
            "M_mkt_market": {
                "description": "Apreciación macroeconómica del activo inmobiliario rural en dólares.",
                "rule": "Tasa histórica de inflación y refugio de valor en USD (+2.0% anual compuesto).",
                "source": "Informes históricos de mercado de tierras de la Bolsa de Comercio de Rosario (BCR).",
            },
        },
    }
