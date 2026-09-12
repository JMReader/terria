from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas import FieldResponse
from app.timelapse.schemas import TimelapseDatasetSummary, TimelapseManifest


def decimal_str(value: float, places: int = 2) -> str:
    """Floats break canonical hashing, so numbers travel as fixed decimal strings."""
    return f"{value:.{places}f}"


def _scaled_int(value: float | None, factor: int) -> int | None:
    """Canonical hashing rejects floats, so measurements travel as scaled integers."""
    if value is None:
        return None
    return int(round(value * factor))


def build_observations(manifests: list[TimelapseManifest]) -> list[dict[str, Any]]:
    """Dated satellite + weather observations, merged per day and free of floats."""
    observations: list[dict[str, Any]] = []
    for manifest in manifests:
        weather_by_date = {day.date: day for day in manifest.weather_daily}
        for frame in manifest.frames:
            weather = weather_by_date.get(frame.local_date)
            observations.append(
                {
                    "date": frame.local_date.isoformat(),
                    "satellite_usable": bool(frame.usable),
                    "ndvi_mean_x1000": _scaled_int(frame.ndvi.mean, 1000),
                    "ndvi_p10_x1000": _scaled_int(frame.ndvi.p10, 1000),
                    "ndvi_p90_x1000": _scaled_int(frame.ndvi.p90, 1000),
                    "precip_mm_x10": (
                        _scaled_int(weather.precipitation_mm, 10) if weather else None
                    ),
                    "precip_7d_mm_x10": (
                        _scaled_int(weather.precipitation_7d_mm, 10) if weather else None
                    ),
                    "temp_min_c_x10": (
                        _scaled_int(weather.temperature_min_c, 10) if weather else None
                    ),
                    "temp_max_c_x10": (
                        _scaled_int(weather.temperature_max_c, 10) if weather else None
                    ),
                }
            )
    observations.sort(key=lambda item: item["date"])
    return observations


def build_sources(manifests: list[TimelapseManifest]) -> list[dict[str, Any]]:
    """Provenance list, deduplicated by source id."""
    sources: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        for source in manifest.sources:
            sources[source.id] = {
                "id": source.id,
                "provider": source.provider,
                "dataset": source.dataset,
                "retrieved_at": source.retrieved_at.isoformat(),
            }
    return [sources[key] for key in sorted(sources)]


def build_snapshot(
    *,
    field: FieldResponse,
    datasets: list[TimelapseDatasetSummary],
    period_from: int,
    period_to: int,
    cert_uid: str,
    schema_version: str,
    prev_hash: str | None,
    issued_at: datetime | None = None,
    observations: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    issued = (issued_at or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    return {
        "schema_version": schema_version,
        "cert_uid": cert_uid,
        "field": {
            "uid": str(field.id),
            "area_ha": decimal_str(field.area_hectares),
            "province": field.province,
        },
        "period": {"from": period_from, "to": period_to},
        "datasets": [
            {
                "id": str(dataset.id),
                "start": dataset.start_date.isoformat(),
                "end": dataset.end_date.isoformat(),
                "status": dataset.status,
                "frames": dataset.frames_count,
                "is_demo": bool(dataset.is_demo),
            }
            for dataset in datasets
        ],
        "observations": observations or [],
        "sources": sources or [],
        "issued_at": issued,
        "prev_snapshot_hash": prev_hash,
    }
