"""Portada NDVI del certificado.

Genera un PNG de NDVI real de Sentinel-2 L2A **sin cuenta Copernicus**, usando el
catálogo STAC y el tiler de Microsoft Planetary Computer (los mismos que ya usa el
motor What-If). El raster se recorta al bounding box del lote certificado.
"""

from __future__ import annotations

import logging

import httpx

from app.schemas import PolygonGeometry

logger = logging.getLogger(__name__)

STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
BBOX_PREVIEW_URL = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox"

NDVI_EXPRESSION = "(B08-B04)/(B08+B04)"


def build_ndvi_preview(
    boundary: PolygonGeometry,
    start_date: str,
    end_date: str,
    *,
    size: int = 384,
    max_cloud: float = 20.0,
) -> bytes | None:
    """PNG NDVI (colormap rdylgn) de la escena menos nubosa del período, o None."""
    ring = boundary.coordinates[0]
    longitudes = [point[0] for point in ring]
    latitudes = [point[1] for point in ring]
    bbox = f"{min(longitudes)},{min(latitudes)},{max(longitudes)},{max(latitudes)}"

    search = {
        "collections": ["sentinel-2-l2a"],
        "intersects": {"type": "Polygon", "coordinates": boundary.coordinates},
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "sortby": [{"field": "eo:cloud_cover", "direction": "asc"}],
        "limit": 1,
    }

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(STAC_SEARCH_URL, json=search)
            response.raise_for_status()
            features = response.json().get("features", [])
            if not features:
                logger.warning("No Sentinel-2 scenes for %s..%s", start_date, end_date)
                return None
            item_id = features[0]["id"]

            preview = client.get(
                f"{BBOX_PREVIEW_URL}/{bbox}.png",
                params=[
                    ("collection", "sentinel-2-l2a"),
                    ("item", item_id),
                    ("assets", "B04"),
                    ("assets", "B08"),
                    ("asset_as_band", "true"),
                    ("expression", NDVI_EXPRESSION),
                    ("rescale", "-0.2,0.8"),
                    ("colormap_name", "rdylgn"),
                    ("width", str(size)),
                ],
            )
            preview.raise_for_status()
            if not preview.content.startswith(b"\x89PNG\r\n\x1a\n"):
                logger.warning("Planetary Computer did not return a PNG for %s", item_id)
                return None
            return preview.content
    except httpx.HTTPError as exc:
        logger.warning("Could not build NDVI preview: %s", exc)
        return None
