from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
import logging

import httpx

from app.config import settings
from app.timelapse.schemas import TimelapseSource, WeatherDaily

logger = logging.getLogger(__name__)


def calculate_7d_precipitation(
    daily_precip: dict[date, float | None],
    target_date: date,
) -> tuple[float | None, str | None]:
    """Calculates rolling 7-day accumulated precipitation inclusively from D-6 to D.

    Rules:
    - If any day in [D-6, D] is missing or None, returns (None, 'INCOMPLETE_7D_WINDOW').
    - If all 7 days are present, returns the rounded sum (0.0 is a valid measurement).
    """
    window = [target_date - timedelta(days=i) for i in range(6, -1, -1)]
    for day in window:
        if day not in daily_precip or daily_precip[day] is None:
            return None, "INCOMPLETE_7D_WINDOW"

    total = sum(daily_precip[day] for day in window)  # type: ignore[arg-type]
    return round(float(total), 2), None


def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> tuple[list[WeatherDaily], list[TimelapseSource], list[str]]:
    """Fetches real historical weather from Open-Meteo (ERA5 reanalysis) for the field centroid.

    Requests starting 6 days before start_date to accurately calculate the 7-day accumulation
    from the very first day of the period.
    """
    missing_reasons: list[str] = []
    sources: list[TimelapseSource] = []
    weather_records: list[WeatherDaily] = []

    api_start_date = start_date - timedelta(days=6)
    params = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "start_date": api_start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(settings.weather_archive_url, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except Exception as exc:
        logger.warning("Failed to fetch historical weather from Open-Meteo: %s", exc)
        missing_reasons.append(f"WEATHER_PROVIDER_ERROR: {exc}")
        return [], [], missing_reasons

    daily_data = data.get("daily", {})
    times: list[str] = daily_data.get("time", [])
    precipitation_sums: list[float | None] = daily_data.get("precipitation_sum", [])
    temperatures_max: list[float | None] = daily_data.get("temperature_2m_max", [])
    temperatures_min: list[float | None] = daily_data.get("temperature_2m_min", [])

    precip_dict: dict[date, float | None] = {}
    temp_min_dict: dict[date, float | None] = {}
    temp_max_dict: dict[date, float | None] = {}

    for idx, time_str in enumerate(times):
        day = date.fromisoformat(time_str)
        p_val = precipitation_sums[idx] if idx < len(precipitation_sums) else None
        t_min = temperatures_min[idx] if idx < len(temperatures_min) else None
        t_max = temperatures_max[idx] if idx < len(temperatures_max) else None

        precip_dict[day] = float(p_val) if p_val is not None else None
        temp_min_dict[day] = float(t_min) if t_min is not None else None
        temp_max_dict[day] = float(t_max) if t_max is not None else None

    # Source metadata
    source_id = "open-meteo-era5"
    sources.append(
        TimelapseSource(
            id=source_id,
            provider="Open-Meteo",
            dataset="Historical Weather API (ERA5 Reanalysis)",
            model="ERA5",
            resolution="~0.25 deg (~25 km)",
            retrieved_at=datetime.now(timezone.utc),
            documentation_url="https://open-meteo.com/en/docs/historical-weather-api",
            attribution="Weather data by Open-Meteo.com under CC BY 4.0",
        )
    )

    # Build weather daily for the requested range [start_date, end_date]
    curr = start_date
    while curr <= end_date:
        p_day = precip_dict.get(curr)
        p_7d, reason_7d = calculate_7d_precipitation(precip_dict, curr)
        t_min = temp_min_dict.get(curr)
        t_max = temp_max_dict.get(curr)

        day_reason: str | None = None
        if p_day is None:
            day_reason = "MISSING_DAILY_WEATHER"
        elif reason_7d is not None:
            day_reason = reason_7d

        weather_records.append(
            WeatherDaily(
                date=curr,
                precipitation_mm=p_day,
                precipitation_7d_mm=p_7d,
                temperature_min_c=t_min,
                temperature_max_c=t_max,
                source_id=source_id,
                missing_reason=day_reason,
            )
        )
        curr += timedelta(days=1)

    return weather_records, sources, missing_reasons
