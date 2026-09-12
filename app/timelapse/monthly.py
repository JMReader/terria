"""Serie mensual de seguimiento del lote.

Agrupa por mes calendario las observaciones satelitales (NDVI de escenas usables)
y el clima diario (lluvia y temperatura), y etiqueta cada mes con su campaña
agrícola. Es la base del trackeo histórico del front y del snapshot de
certificación (`terria.cert`). Sin floats: todo escalado a enteros.
"""

from __future__ import annotations

from collections import defaultdict

from app.timelapse.schemas import MonthlySummary, TimelapseManifest, TimelapseFrame, WeatherDaily


def campaign_of(month: str) -> str:
    """Campaña agrícola del mes: jul–dic → 'YYYY/YY+1'; ene–jun → 'YYYY-1/YY'."""
    year, month_number = int(month[:4]), int(month[5:7])
    if month_number >= 7:
        return f"{year}/{(year + 1) % 100:02d}"
    return f"{year - 1}/{year % 100:02d}"


def _scaled(value: float | None, factor: int) -> int | None:
    if value is None:
        return None
    return int(round(value * factor))


def build_monthly_series(manifests: list[TimelapseManifest]) -> list[MonthlySummary]:
    """Serie mensual ordenada, sin duplicar días repetidos entre datasets."""
    frames_by_month: dict[str, list[TimelapseFrame]] = defaultdict(list)
    weather_by_month: dict[str, list[WeatherDaily]] = defaultdict(list)
    seen_frames: set[tuple[str, object]] = set()
    seen_weather: set[tuple[str, object]] = set()

    for manifest in manifests:
        for frame in manifest.frames:
            key = frame.local_date.strftime("%Y-%m")
            dedup = ("frame", frame.local_date)
            if dedup in seen_frames:
                continue
            seen_frames.add(dedup)
            frames_by_month[key].append(frame)
        for day in manifest.weather_daily:
            key = day.date.strftime("%Y-%m")
            dedup = ("weather", day.date)
            if dedup in seen_weather:
                continue
            seen_weather.add(dedup)
            weather_by_month[key].append(day)

    months = sorted(set(frames_by_month) | set(weather_by_month))
    series: list[MonthlySummary] = []
    for month in months:
        month_frames = frames_by_month.get(month, [])
        usable = [f for f in month_frames if f.usable and f.ndvi.mean is not None]
        ndvi_means = [f.ndvi.mean for f in usable]

        days = weather_by_month.get(month, [])
        precip = [d.precipitation_mm for d in days if d.precipitation_mm is not None]
        temp_min = [d.temperature_min_c for d in days if d.temperature_min_c is not None]
        temp_max = [d.temperature_max_c for d in days if d.temperature_max_c is not None]
        daily_means = [
            (d.temperature_min_c + d.temperature_max_c) / 2
            for d in days
            if d.temperature_min_c is not None and d.temperature_max_c is not None
        ]

        series.append(
            MonthlySummary(
                month=month,
                campaign=campaign_of(month),
                satellite_scenes=len(month_frames),
                usable_scenes=len(usable),
                ndvi_mean_x1000=_scaled(
                    sum(ndvi_means) / len(ndvi_means) if ndvi_means else None, 1000
                ),
                ndvi_max_x1000=_scaled(max(ndvi_means) if ndvi_means else None, 1000),
                ndvi_min_x1000=_scaled(min(ndvi_means) if ndvi_means else None, 1000),
                precip_mm_x10=_scaled(sum(precip), 10) if precip else None,
                temp_mean_c_x10=_scaled(
                    sum(daily_means) / len(daily_means) if daily_means else None, 10
                ),
                temp_min_c_x10=_scaled(min(temp_min) if temp_min else None, 10),
                temp_max_c_x10=_scaled(max(temp_max) if temp_max else None, 10),
            )
        )
    return series
