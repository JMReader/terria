from __future__ import annotations

import hashlib
import json
import math
from typing import Any
from uuid import UUID

from app.what_if.geometry import parse_geometry_input
from app.what_if.providers import (
    build_audit_urls,
    fetch_historical_management_ndvi,
    fetch_real_climate,
    fetch_regional_mean_ndvi,
    fetch_sar_moisture,
    fetch_soil_data,
    fetch_topography_slope,
    generate_spatial_candidates,
    get_official_benchmarks,
)
from app.what_if.schemas import (
    CandidateLot,
    FeatureVector5D,
    ModelMetrics,
    SimulationFinancials,
    SimulationResults,
    WhatIfSimulationResponse,
)
from app.what_if.territory import resolve_territorial_context


def compute_content_hash(
    lot_data: dict[str, Any], params_data: dict[str, Any], frozen_inputs: dict[str, Any]
) -> str:
    """Calcula el hash determinista SHA-256 de los insumos congelados y parámetros del lote,

    conforme al diseño de certificación trazable (TERRIA Data Schema Spec v0.1 / cert.inputs / Solana memo).
    """
    payload_to_hash = {
        "schema_version": "0.1",
        "algorithm_version": "2.1.0",
        "lot": lot_data,
        "params": params_data,
        "frozen_inputs": frozen_inputs,
    }
    canonical_json = json.dumps(payload_to_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def extract_raw_features(vec: FeatureVector5D) -> list[float]:
    """Convierte el vector 5D a una lista numérica plana."""
    texture_ratio = vec.f_soil_clay_pct / max(1.0, (vec.f_soil_clay_pct + vec.f_soil_sand_pct))
    return [
        texture_ratio,
        vec.f_topo_slope_deg,
        vec.f_init_water_radar_db,
        vec.f_water_bal_mm,
        vec.f_history_ndvi_max,
    ]


def normalize_vectors(
    base_vec: FeatureVector5D, candidates: list[CandidateLot]
) -> tuple[list[float], list[CandidateLot]]:
    """Normaliza MinMax las 5 dimensiones sobre el universo regional (base + candidatos)

    en Python puro sin dependencias externas pesadas.
    """
    all_raw = [extract_raw_features(base_vec)]
    for c in candidates:
        all_raw.append(extract_raw_features(c.vector_5d))

    num_dims = 5
    mins = [min(row[d] for row in all_raw) for d in range(num_dims)]
    maxs = [max(row[d] for row in all_raw) for d in range(num_dims)]
    ranges = [(maxs[d] - mins[d]) if (maxs[d] - mins[d]) != 0 else 1.0 for d in range(num_dims)]

    def scale(row: list[float]) -> list[float]:
        return [(row[d] - mins[d]) / ranges[d] for d in range(num_dims)]

    base_norm = scale(all_raw[0])
    base_vec.normalized_vector = base_norm

    for i, c in enumerate(candidates):
        c_norm = scale(all_raw[i + 1])
        c.vector_5d.normalized_vector = c_norm

    return base_norm, candidates


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calcula la similitud del coseno entre dos vectores numéricos en Python puro."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def find_twin_lots(
    base_vec: FeatureVector5D,
    candidates: list[CandidateLot],
    top_pct: float = 0.05,
    min_lots: int = 5,
) -> tuple[list[CandidateLot], float]:
    """Aplica similitud del coseno sobre el espacio 5D y selecciona el Top 5% más parecido."""
    base_norm, candidates = normalize_vectors(base_vec, candidates)

    for c in candidates:
        sim = cosine_similarity(base_norm, c.vector_5d.normalized_vector or [])
        c.similarity_score = round(sim, 4)

    candidates.sort(key=lambda x: x.similarity_score, reverse=True)
    cutoff = max(min_lots, int(len(candidates) * top_pct))
    twin_lots = candidates[:cutoff]

    avg_score = round(sum(t.similarity_score for t in twin_lots) / len(twin_lots), 4)
    return twin_lots, avg_score


def run_what_if_simulation(
    *,
    geometry_data: Any,
    lot_name: str,
    target_year: int,
    simulated_crop: str,
    real_crop: str = "soja_1ra",
    real_margin_usd_ha: float = 350.0,
    real_yield_tn_ha: float | None = None,
    field_id: UUID | None = None,
    include_audit: bool = True,
) -> WhatIfSimulationResponse:
    """Ejecuta el pipeline completo del simulador agronómico What-If."""
    c_lat, c_lon, surface_ha, bbox = parse_geometry_input(geometry_data)

    territory = resolve_territorial_context(c_lat, c_lon)
    dept = territory["department"]
    prov = territory["province"]

    benchmarks = get_official_benchmarks(dept, prov, simulated_crop, target_year)

    soil = fetch_soil_data(c_lat, c_lon)
    topo = fetch_topography_slope(c_lat, c_lon)
    climate = fetch_real_climate(c_lat, c_lon, target_year)
    sar = fetch_sar_moisture(c_lat, c_lon, target_year)
    hist = fetch_historical_management_ndvi(c_lat, c_lon, target_year)

    regional_ndvi_info = fetch_regional_mean_ndvi(
        c_lat, c_lon, target_year, climate.get("water_balance_mm")
    )
    zone_ndvi = regional_ndvi_info.get("zone_mean_ndvi", 0.45)

    base_vector = FeatureVector5D(
        f_soil_clay_pct=soil["clay_pct"],
        f_soil_sand_pct=soil["sand_pct"],
        f_topo_slope_deg=topo["mean_slope_deg"],
        f_init_water_radar_db=sar["backscatter_ratio_db"],
        f_water_bal_mm=climate["water_balance_mm"],
        f_history_ndvi_max=hist["avg_max_ndvi"],
        dem_elevation_m=topo.get("elevation_m"),
        s1_scene_id=sar.get("scene_id"),
        s2_scene_id=hist.get("scene_id"),
        soil_source=soil.get("source"),
    )

    candidates = generate_spatial_candidates(
        center_lat=c_lat,
        center_lon=c_lon,
        radius_km=50.0,
        crop=simulated_crop,
        count=180,
        base_vector=base_vector,
    )

    twin_lots, avg_score = find_twin_lots(base_vector, candidates)

    # Proyección de rendimiento
    avg_twins_ndvi = sum(t.vector_5d.f_history_ndvi_max for t in twin_lots) / len(twin_lots)
    delta_ndvi = (avg_twins_ndvi - zone_ndvi) / max(0.2, zone_ndvi)
    delta_clamped = max(-0.35, min(0.35, delta_ndvi))

    official_yield = benchmarks["dept_yield_sagyp_tn_ha"]
    projected_yield = round(official_yield * (1.0 + delta_clamped), 2)

    price = benchmarks["matba_price_harvest_usd_tn"]
    cost = benchmarks["bcr_cost_implantacion_usd_ha"]
    gross_income = round(projected_yield * price, 2)
    net_margin = round(gross_income - cost, 2)
    diff_margin = round(net_margin - real_margin_usd_ha, 2)
    total_lot_diff = round(diff_margin * surface_ha, 2)

    crop_label = benchmarks["crop_label"]
    if diff_margin > 0:
        recommendation = (
            f"Rotación favorable: {crop_label} en {target_year} habría superado el margen real "
            f"en +USD {diff_margin:.2f}/ha (+USD {total_lot_diff:,.2f} en el total del lote de {surface_ha:.1f} ha)."
        )
    else:
        recommendation = (
            f"Decisión real acertada: La rotación con {crop_label} en {target_year} habría dejado "
            f"un margen menor en USD {diff_margin:.2f}/ha (-USD {abs(total_lot_diff):,.2f} en el total del lote)."
        )

    # Insumos congelados para certificación on-chain
    frozen_inputs = {
        "environmental_vector_5d": {
            "soil_clay_pct": base_vector.f_soil_clay_pct,
            "soil_sand_pct": base_vector.f_soil_sand_pct,
            "mean_slope_deg": base_vector.f_topo_slope_deg,
            "elevation_dem_m": base_vector.dem_elevation_m,
            "radar_backscatter_db": base_vector.f_init_water_radar_db,
            "water_balance_mm": base_vector.f_water_bal_mm,
            "historical_ndvi_max": base_vector.f_history_ndvi_max,
        },
        "regional_calibration": {
            "zone_mean_ndvi": zone_ndvi,
            "zone_ndvi_source": regional_ndvi_info.get("source"),
            "official_sagyp_yield_tn_ha": official_yield,
            "sagyp_citation": benchmarks["source_yield"],
            "matba_price_usd_tn": price,
            "bcr_cost_usd_ha": cost,
        },
    }

    audit_urls = build_audit_urls(c_lat, c_lon, target_year) if include_audit else None

    # Hash determinista de certificación
    lot_data = {
        "name": lot_name,
        "centroid": [c_lat, c_lon],
        "surface_ha": surface_ha,
        "department": dept,
        "province": prov,
    }
    params_data = {
        "target_year": target_year,
        "simulated_crop": simulated_crop,
        "real_crop": real_crop,
        "real_margin_usd_ha": real_margin_usd_ha,
    }
    content_hash = compute_content_hash(lot_data, params_data, frozen_inputs)

    return WhatIfSimulationResponse(
        status="success",
        schema_version="0.1",
        algorithm_version="2.1.0",
        field_id=field_id,
        lot_name=lot_name,
        surface_ha=surface_ha,
        target_year=target_year,
        simulated_crop=simulated_crop,
        real_crop=real_crop,
        content_hash=content_hash,
        model_metrics=ModelMetrics(
            candidate_lots_scanned=len(candidates),
            strict_twin_lots_matched=len(twin_lots),
            avg_similarity_score=avg_score,
            dimensions_analyzed=[
                "soil_texture",
                "topography_slope",
                "sar_radar_moisture",
                "net_water_balance",
                "historical_management",
            ],
            zone_mean_ndvi=zone_ndvi,
        ),
        results=SimulationResults(
            projected_yield_tn_ha=projected_yield,
            benchmark_dept_yield_tn_ha=official_yield,
            financials=SimulationFinancials(
                gross_income_usd_ha=gross_income,
                costs_usd_ha=cost,
                net_margin_usd_ha=net_margin,
                real_net_margin_usd_ha=real_margin_usd_ha,
                diff_net_margin_usd_ha=diff_margin,
                total_lot_diff_usd=total_lot_diff,
            ),
            recommendation=recommendation,
        ),
        audit_urls=audit_urls,
        frozen_inputs=frozen_inputs,
    )
