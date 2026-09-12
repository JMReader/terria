from __future__ import annotations

from datetime import date

from app.timelapse.schemas import (
    FrameQuality,
    SatelliteState,
    TimelapseManifest,
    TimelineState,
    WeatherState,
)


def compute_timeline_state(
    manifest: TimelapseManifest,
    selected_date: date,
) -> TimelineState:
    """Deterministic temporal selector for a given date over a loaded manifest.

    Temporal rules:
    - Weather corresponds strictly to the selected_date.
    - Satellite corresponds to the most recent usable observation with local_date <= selected_date.
    - Never uses future captures or interpolates values.
    - If age_days > max_image_age_days, satellite is null and missing reason is added.
    - Missing weather or satellite reasons are recorded without replacing zeros.
    """
    missing_reasons: list[str] = list(manifest.missing_reasons)

    # 1. Weather corresponds directly to selected_date
    weather_entry = next((w for w in manifest.weather_daily if w.date == selected_date), None)
    if weather_entry is not None:
        weather_state = WeatherState(
            date=weather_entry.date,
            precipitation_mm=weather_entry.precipitation_mm,
            precipitation_7d_mm=weather_entry.precipitation_7d_mm,
            temperature_min_c=weather_entry.temperature_min_c,
            temperature_max_c=weather_entry.temperature_max_c,
        )
        if weather_entry.missing_reason:
            missing_reasons.append(f"WEATHER_{weather_entry.missing_reason}")
    else:
        weather_state = WeatherState(
            date=selected_date,
            precipitation_mm=None,
            precipitation_7d_mm=None,
            temperature_min_c=None,
            temperature_max_c=None,
        )
        missing_reasons.append(f"NO_WEATHER_FOR_DATE: No weather recorded for {selected_date}")

    # 2. Satellite corresponds to latest usable observation on or prior to selected_date
    # Never future captures!
    candidate_frames = [
        f for f in manifest.frames
        if f.usable and f.local_date <= selected_date
    ]
    candidate_frames.sort(key=lambda f: (f.local_date, f.observed_at), reverse=True)

    satellite_state: SatelliteState | None = None
    max_age_days = manifest.playback.max_image_age_days

    if not candidate_frames:
        missing_reasons.append(
            f"NO_SATELLITE_OBSERVATION: No usable observation on or before {selected_date}"
        )
    else:
        latest_frame = candidate_frames[0]
        age_days = (selected_date - latest_frame.local_date).days
        if age_days > max_age_days:
            missing_reasons.append(
                f"MAX_IMAGE_AGE_EXCEEDED: Most recent observation is {age_days} days old (limit: {max_age_days} days)"
            )
        else:
            satellite_state = SatelliteState(
                frame_id=latest_frame.id,
                observed_at=latest_frame.observed_at,
                age_days=age_days,
                ndvi=latest_frame.ndvi,
                quality=FrameQuality(
                    valid_area_fraction=latest_frame.valid_area_fraction,
                    valid_pixel_count=latest_frame.valid_pixel_count,
                ),
                assets=latest_frame.assets,
            )

    return TimelineState(
        selected_date=selected_date,
        dataset_id=manifest.dataset_id,
        geometry_version_id=manifest.geometry_version_id,
        satellite=satellite_state,
        weather=weather_state,
        sources=manifest.sources,
        missing_reasons=missing_reasons,
        is_demo=manifest.is_demo,
    )
