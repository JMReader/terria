from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas import PolygonGeometry, StrictModel


class CropMetadata(StrictModel):
    id: str
    name: str
    season: str
    category: str
    sowing_window: str
    description: str


SAGYP_CROPS_CATALOG: dict[str, CropMetadata] = {
    "maiz": CropMetadata(
        id="maiz",
        name="Maíz",
        season="Gruesa",
        category="Cereal",
        sowing_window="Septiembre (Temprano) / Diciembre (Tardío)",
        description="Aporte clave de materia orgánica y balance de carbono en la rotación.",
    ),
    "soja_1ra": CropMetadata(
        id="soja_1ra",
        name="Soja de 1ra",
        season="Gruesa",
        category="Oleaginosa",
        sowing_window="Octubre - Noviembre",
        description="Principal oleaginosa estival en secano de la región pampeana.",
    ),
    "soja_2da": CropMetadata(
        id="soja_2da",
        name="Soja de 2da",
        season="Gruesa",
        category="Oleaginosa",
        sowing_window="Diciembre - Enero (Post-cosecha de trigo/cebada)",
        description="Siembra inmediata tras la cosecha del cereal de invierno.",
    ),
    "trigo": CropMetadata(
        id="trigo",
        name="Trigo Pan",
        season="Fina",
        category="Cereal",
        sowing_window="Mayo - Julio",
        description="Cereal de invierno por excelencia para cobertura y puente verde.",
    ),
    "girasol": CropMetadata(
        id="girasol",
        name="Girasol",
        season="Gruesa",
        category="Oleaginosa",
        sowing_window="Agosto - Octubre",
        description="Alta eficiencia en el uso del agua y rusticidad ante anomalías de déficit.",
    ),
    "cebada": CropMetadata(
        id="cebada",
        name="Cebada Cervecera",
        season="Fina",
        category="Cereal",
        sowing_window="Mayo - Julio",
        description="Alternativa al trigo con liberación temprana del lote para el cultivo de 2da.",
    ),
    "sorgo": CropMetadata(
        id="sorgo",
        name="Sorgo Granífero",
        season="Gruesa",
        category="Cereal",
        sowing_window="Octubre - Diciembre",
        description="Excelente adaptación a condiciones de estrés térmico e hídrico severo.",
    ),
    "mani": CropMetadata(
        id="mani",
        name="Maní",
        season="Gruesa",
        category="Especialidad",
        sowing_window="Octubre - Noviembre",
        description="Especialidad de alto valor económico concentrada en el área central cordobesa.",
    ),
    "algodon": CropMetadata(
        id="algodon",
        name="Algodón",
        season="Gruesa",
        category="Industrial",
        sowing_window="Octubre - Diciembre",
        description="Cultivo industrial con adaptación a franjas subhúmedas y cálidas.",
    ),
    "colza": CropMetadata(
        id="colza",
        name="Colza / Canola",
        season="Fina",
        category="Oleaginosa",
        sowing_window="Abril - Mayo",
        description="Oleaginosa de invierno de maduración temprana para anteceder al maíz tardío.",
    ),
}


class FeatureVector5D(StrictModel):
    f_soil_clay_pct: float = Field(..., description="% Arcilla promedio")
    f_soil_sand_pct: float = Field(..., description="% Arena promedio")
    f_topo_slope_deg: float = Field(..., description="Pendiente media en grados")
    f_init_water_radar_db: float = Field(..., description="Retrodispersión radar Sentinel-1 (dB)")
    f_water_bal_mm: float = Field(..., description="Balance hídrico neto lluvia - ETo (mm)")
    f_history_ndvi_max: float = Field(..., description="NDVI estival máximo histórico Sentinel-2")
    dem_elevation_m: float | None = None
    s1_scene_id: str | None = None
    s2_scene_id: str | None = None
    soil_source: str | None = None
    normalized_vector: list[float] | None = None


class CandidateLot(StrictModel):
    lot_id: str
    lat: float
    lon: float
    distance_km: float
    crop: str
    vector_5d: FeatureVector5D
    similarity_score: float = 0.0


# --- Solicitudes a la API ---


class FieldWhatIfRequest(StrictModel):
    """Parámetros para ejecutar simulación sobre un campo persistido."""
    target_year: int = Field(2023, ge=2015, le=2030, description="Campaña agronómica analizada")
    simulated_crop: str = Field("maiz", description="Cultivo contrafáctico a evaluar")
    real_crop: str = Field("soja_1ra", description="Cultivo cosechado en la realidad")
    real_margin_usd_ha: float | None = Field(350.0, description="Margen neto real obtenido (USD/ha)")
    real_yield_tn_ha: float | None = Field(None, description="Rendimiento real cosechado (tn/ha)")
    include_audit: bool = Field(True, description="Incluir deep links públicos y auditoría")


class WhatIfSimulateRequest(StrictModel):
    """Parámetros para simulación standalone con geometría GeoJSON directa."""
    name: str = Field("Lote Simulado", max_length=120)
    boundary: PolygonGeometry | None = None
    coordinates: list[list[float]] | None = None
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    area_hectares: float | None = None
    target_year: int = Field(2023, ge=2015, le=2030)
    simulated_crop: str = Field("maiz")
    real_crop: str = Field("soja_1ra")
    real_margin_usd_ha: float = Field(350.0)
    real_yield_tn_ha: float | None = None
    include_audit: bool = Field(True)


# --- Respuestas de la API ---


class ModelMetrics(StrictModel):
    candidate_lots_scanned: int
    strict_twin_lots_matched: int
    avg_similarity_score: float
    dimensions_analyzed: list[str]
    zone_mean_ndvi: float


class SimulationFinancials(StrictModel):
    gross_income_usd_ha: float
    costs_usd_ha: float
    net_margin_usd_ha: float
    real_net_margin_usd_ha: float
    diff_net_margin_usd_ha: float
    total_lot_diff_usd: float


class SimulationResults(StrictModel):
    projected_yield_tn_ha: float
    benchmark_dept_yield_tn_ha: float
    financials: SimulationFinancials
    recommendation: str


class WhatIfSimulationResponse(StrictModel):
    status: Literal["success"] = "success"
    schema_version: str = "0.1"
    algorithm_version: str = "2.1.0"
    field_id: UUID | None = None
    lot_name: str
    surface_ha: float
    target_year: int
    simulated_crop: str
    real_crop: str
    content_hash: str
    model_metrics: ModelMetrics
    results: SimulationResults
    audit_urls: dict[str, str] | None = None
    frozen_inputs: dict[str, Any] | None = None


# --- Verificación de Veracidad / Benchmarks ---


class BenchmarkItem(StrictModel):
    id: str
    name: str
    lat: float
    lon: float
    province: str
    department: str
    description: str
    expected_soil_order: str
    expected_clay_pct_range: str
    documented_yield_range: str


class BenchmarkListResponse(StrictModel):
    benchmarks: list[BenchmarkItem]


class VerificationRequest(StrictModel):
    benchmark_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    target_year: int = 2023
    crop: str = "maiz"


class VerificationResponse(StrictModel):
    status: Literal["verified"] = "verified"
    benchmark: str
    coordinates: dict[str, float]
    dimensions: dict[str, Any]
    historical_ground_truth: dict[str, Any]
    audit_urls: dict[str, str]
    content_hash: str
    verdict: str
