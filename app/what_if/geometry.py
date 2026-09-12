from __future__ import annotations

import math
from typing import Any

from app.schemas import PolygonGeometry


def calculate_shoelace_area_ha(coords: list[list[float]]) -> float:
    """Calcula el área exacta en hectáreas a partir de coordenadas [lon, lat]

    utilizando la fórmula de Gauss / Shoelace con proyección geodésica local.
    """
    if len(coords) < 3:
        return 0.0

    pts = list(coords)
    if pts[0] == pts[-1] and len(pts) > 3:
        pts = pts[:-1]

    n = len(pts)
    if n < 3:
        return 0.0

    avg_lat = sum(p[1] for p in pts) / n
    m_lat = 111139.0
    m_lon = 111139.0 * math.cos(math.radians(avg_lat))

    xy = [(p[0] * m_lon, p[1] * m_lat) for p in pts]

    area_m2 = 0.5 * abs(
        sum(xy[i][0] * xy[(i + 1) % n][1] - xy[(i + 1) % n][0] * xy[i][1] for i in range(n))
    )
    return round(area_m2 / 10000.0, 2)


def calculate_centroid(coords: list[list[float]]) -> tuple[float, float]:
    """Calcula el centroide geométrico (lat, lon) de una lista de vértices [lon, lat]."""
    pts = list(coords)
    if pts[0] == pts[-1] and len(pts) > 3:
        pts = pts[:-1]
    n = len(pts)
    if n == 0:
        return 0.0, 0.0
    avg_lon = sum(p[0] for p in pts) / n
    avg_lat = sum(p[1] for p in pts) / n
    return round(avg_lat, 5), round(avg_lon, 5)


def parse_geometry_input(
    data: Any,
    fallback_ha: float = 0.0,
) -> tuple[float, float, float, list[float]]:
    """Parsea estructuras PolygonGeometry, GeoJSON (Polygon, LineString) o listas de puntos.

    Retorna: (centroid_lat, centroid_lon, surface_ha, bbox [min_lon, min_lat, max_lon, max_lat])
    """
    if isinstance(data, PolygonGeometry):
        ring = data.coordinates[0]
        area_ha = calculate_shoelace_area_ha(ring)
        c_lat, c_lon = calculate_centroid(ring)
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        return c_lat, c_lon, area_ha, [min(lons), min(lats), max(lons), max(lats)]

    if isinstance(data, dict):
        if data.get("type") == "Feature":
            data = data.get("geometry", {})

        geom_type = data.get("type")
        raw_coords = data.get("coordinates", [])

        if geom_type == "Polygon":
            ring = raw_coords[0] if raw_coords else []
            area_ha = calculate_shoelace_area_ha(ring)
            c_lat, c_lon = calculate_centroid(ring)
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            return c_lat, c_lon, area_ha, [min(lons), min(lats), max(lons), max(lats)]

        if geom_type in ["LineString", "MultiPoint"]:
            area_ha = calculate_shoelace_area_ha(raw_coords)
            c_lat, c_lon = calculate_centroid(raw_coords)
            lons = [p[0] for p in raw_coords]
            lats = [p[1] for p in raw_coords]
            return c_lat, c_lon, area_ha, [min(lons), min(lats), max(lons), max(lats)]

        if geom_type == "Point":
            lon, lat = raw_coords[0], raw_coords[1]
            return lat, lon, fallback_ha, [lon, lat, lon, lat]

    if isinstance(data, list):
        area_ha = calculate_shoelace_area_ha(data)
        c_lat, c_lon = calculate_centroid(data)
        lons = [p[0] for p in data]
        lats = [p[1] for p in data]
        return c_lat, c_lon, area_ha, [min(lons), min(lats), max(lons), max(lats)]

    raise ValueError("Formato de geometría no reconocido o coordenadas vacías.")
