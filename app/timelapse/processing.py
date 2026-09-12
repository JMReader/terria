from __future__ import annotations

from datetime import date, datetime, timezone
import logging
from uuid import UUID, uuid4

from app.config import settings
from app.schemas import PolygonGeometry
from app.timelapse.providers.sentinel import sentinel_provider
from app.timelapse.providers.synthetic import generate_synthetic_demo
from app.timelapse.providers.weather import fetch_historical_weather
from app.timelapse.schemas import (
    PlaybackConfig,
    TimelapseManifest,
)

logger = logging.getLogger(__name__)


def process_timelapse_dataset(
    field_id: UUID,
    geometry_version_id: UUID,
    boundary: PolygonGeometry,
    area_hectares: float,
    start_date: date,
    end_date: date,
    layers: list[str] | None = None,
    is_demo: bool = False,
    dataset_id: UUID | None = None,
) -> TimelapseManifest:
    """Orchestrates dataset generation either via synthetic generator or real providers."""
    ds_id = dataset_id or uuid4()
    now_utc = datetime.now(timezone.utc)

    if is_demo:
        logger.info("Generating synthetic demo dataset for field %s", field_id)
        return generate_synthetic_demo(
            field_id=field_id,
            geometry_version_id=geometry_version_id,
            boundary=boundary,
            area_hectares=area_hectares,
            start_date=start_date,
            end_date=end_date,
            dataset_id=ds_id,
        )

    # Real data pipeline
    logger.info("Processing real data timelapse for field %s (%s to %s)", field_id, start_date, end_date)
    ring = boundary.coordinates[0]
    n_pts = len(ring) - 1
    centroid_lon = sum(p[0] for p in ring[:-1]) / n_pts
    centroid_lat = sum(p[1] for p in ring[:-1]) / n_pts

    # 1. Weather
    weather_records, weather_sources, weather_reasons = fetch_historical_weather(
        latitude=centroid_lat,
        longitude=centroid_lon,
        start_date=start_date,
        end_date=end_date,
    )

    # 2. Satellite
    frames, sat_sources, sat_reasons = sentinel_provider.fetch_frames(
        field_id=field_id,
        dataset_id=ds_id,
        boundary_coords=boundary.coordinates,
        start_date=start_date,
        end_date=end_date,
    )

    all_sources = weather_sources + sat_sources
    all_reasons = weather_reasons + sat_reasons

    # Status evaluation
    if frames and weather_records:
        ds_status = "ready"
    elif frames or weather_records:
        ds_status = "partial"
    else:
        ds_status = "failed"

    return TimelapseManifest(
        dataset_id=ds_id,
        schema_version="1",
        processing_version=settings.timelapse_processing_version,
        field_id=field_id,
        geometry_version_id=geometry_version_id,
        boundary=boundary,
        area_hectares=area_hectares,
        start_date=start_date,
        end_date=end_date,
        timezone="America/Argentina/Cordoba",
        status=ds_status,  # type: ignore[arg-type]
        generated_at=now_utc,
        is_demo=False,
        playback=PlaybackConfig(
            max_image_age_days=settings.timelapse_max_image_age_days,
            step_days=1,
        ),
        frames=frames,
        weather_daily=weather_records,
        sources=all_sources,
        missing_reasons=all_reasons,
    )
