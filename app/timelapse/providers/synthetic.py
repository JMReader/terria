from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import math
import struct
from uuid import UUID, uuid4
import zlib

from app.config import settings
from app.schemas import PolygonGeometry
from app.timelapse.providers.weather import calculate_7d_precipitation
from app.timelapse.schemas import (
    AssetResponse,
    NdviMetrics,
    PlaybackConfig,
    TimelapseFrame,
    TimelapseManifest,
    TimelapseSource,
    WeatherDaily,
)


def _make_png(width: int, height: int, rgba_bytes: bytes) -> bytes:
    """Generates standard PNG RGBA image bytes in pure Python."""
    stride = width * 4
    raw_lines = bytearray()
    for y in range(height):
        raw_lines.append(0)  # Filter type 0 (None)
        raw_lines.extend(rgba_bytes[y * stride : (y + 1) * stride])
    compressed = zlib.compress(bytes(raw_lines), level=6)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def _generate_field_texture(
    width: int,
    height: int,
    layer: str,
    ndvi_val: float,
) -> bytes:
    """Renders a 256x256 RGBA image representing the agricultural parcel."""
    pixels = bytearray(width * height * 4)

    cx, cy = width / 2.0, height / 2.0
    rx, ry = width * 0.38, height * 0.38

    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            # Elliptical / polygonal parcel boundary with slight rotation
            nx = (x - cx) * math.cos(0.2) - (y - cy) * math.sin(0.2)
            ny = (x - cx) * math.sin(0.2) + (y - cy) * math.cos(0.2)
            dist_sq = (nx / rx) ** 2 + (ny / ry) ** 2

            if dist_sq > 1.0:
                # Transparent outside boundary
                pixels[idx : idx + 4] = b"\x00\x00\x00\x00"
            elif dist_sq > 0.94:
                # Boundary outline (white / dark border)
                pixels[idx : idx + 4] = b"\xff\xff\xff\xcc"
            else:
                # Inside parcel: add agricultural row texture
                furrow = math.sin((x + y) * 0.4) * 0.08
                local_ndvi = max(0.0, min(1.0, ndvi_val + furrow))

                if layer == "rgb":
                    # Natural crop color: blends from brown earth to vibrant crop green
                    r = int(140 * (1.0 - local_ndvi) + 45 * local_ndvi)
                    g = int(105 * (1.0 - local_ndvi) + 165 * local_ndvi)
                    b = int(75 * (1.0 - local_ndvi) + 50 * local_ndvi)
                    pixels[idx : idx + 4] = bytes([r, g, b, 240])
                else:
                    # NDVI false color: Red (<0.2) -> Yellow (0.4) -> Lush Green (>0.7)
                    if local_ndvi < 0.3:
                        r, g, b = 220, int(local_ndvi * 500), 40
                    elif local_ndvi < 0.6:
                        t = (local_ndvi - 0.3) / 0.3
                        r = int(220 * (1.0 - t) + 120 * t)
                        g = int(150 * (1.0 - t) + 210 * t)
                        b = 30
                    else:
                        t = (local_ndvi - 0.6) / 0.4
                        r = int(120 * (1.0 - t) + 25 * t)
                        g = int(210 * (1.0 - t) + 175 * t)
                        b = int(30 * (1.0 - t) + 40 * t)
                    pixels[idx : idx + 4] = bytes([r, g, b, 245])

    return _make_png(width, height, bytes(pixels))


def generate_synthetic_demo(
    field_id: UUID,
    geometry_version_id: UUID,
    boundary: PolygonGeometry,
    area_hectares: float,
    start_date: date,
    end_date: date,
    dataset_id: UUID | None = None,
) -> TimelapseManifest:
    """Generates a complete synthetic demonstration dataset with realistic weather,

    crop growth curves, cloudy observations, max age gaps, and real PNG image assets.
    """
    ds_id = dataset_id or uuid4()
    now_utc = datetime.now(timezone.utc)
    total_days = (end_date - start_date).days + 1

    # 1. Generate daily weather with realistic summer Argentine temperatures and rain events
    daily_precip_map: dict[date, float | None] = {}
    weather_daily: list[WeatherDaily] = []

    # Deterministic rain days
    rain_days_indices = {4, 12, 23, 24, 38, 51, 67, 80}

    # Pre-generate precip map including 6 prior days for rolling 7-day accumulation
    for offset in range(-6, total_days):
        day = start_date + timedelta(days=offset)
        if offset in rain_days_indices:
            rain_mm = round(12.0 + ((offset * 7) % 28) + 3.5, 1)
        else:
            rain_mm = 0.0  # 0.0 mm is valid zero rain!
        daily_precip_map[day] = rain_mm

    for offset in range(total_days):
        day = start_date + timedelta(days=offset)
        p_day = daily_precip_map[day]
        p_7d, reason_7d = calculate_7d_precipitation(daily_precip_map, day)

        # Realistic seasonal temperatures
        temp_cycle = math.sin(offset / max(1, total_days) * math.pi)
        temp_min = round(16.5 + temp_cycle * 3.5 + math.sin(offset) * 1.5, 1)
        temp_max = round(28.0 + temp_cycle * 4.0 + math.cos(offset) * 2.0, 1)

        weather_daily.append(
            WeatherDaily(
                date=day,
                precipitation_mm=p_day,
                precipitation_7d_mm=p_7d,
                temperature_min_c=temp_min,
                temperature_max_c=temp_max,
                source_id="synthetic-weather-engine",
                missing_reason=reason_7d,
            )
        )

    # 2. Generate satellite frames with realistic crop curve and a >10 day gap to test max age
    # Frame day offsets within the period:
    # 3 (emerging, 0.28)
    # 9 (cloudy, unusable, 0.35 valid area fraction)
    # 15 (vegetative growth, 0.46)
    # 25 (canopy development, 0.63)
    # 38 (peak vigor, 0.79)
    # -- GAP of 14 DAYS (from day 38 to day 52) -> Days 49, 50, 51 will have age > 10! --
    # 52 (senescence begin, 0.73)
    # 65 (maturation, 0.54)
    # 78 (pre-harvest, 0.33)

    frame_configs = [
        {"offset": 3, "ndvi": 0.28, "usable": True, "valid_frac": 0.98, "reason": None},
        {"offset": 9, "ndvi": 0.35, "usable": False, "valid_frac": 0.35, "reason": "CLOUDY_SCENE"},
        {"offset": 15, "ndvi": 0.46, "usable": True, "valid_frac": 0.95, "reason": None},
        {"offset": 25, "ndvi": 0.63, "usable": True, "valid_frac": 0.92, "reason": None},
        {"offset": 38, "ndvi": 0.79, "usable": True, "valid_frac": 0.97, "reason": None},
        {"offset": 52, "ndvi": 0.73, "usable": True, "valid_frac": 0.94, "reason": None},
        {"offset": 65, "ndvi": 0.54, "usable": True, "valid_frac": 0.91, "reason": None},
        {"offset": 78, "ndvi": 0.33, "usable": True, "valid_frac": 0.89, "reason": None},
    ]

    frames: list[TimelapseFrame] = []
    assets_dir = settings.assets_dir

    for cfg in frame_configs:
        offset_days = cfg["offset"]
        if offset_days >= total_days:
            continue
        obs_date = start_date + timedelta(days=offset_days)
        frame_id = uuid4()
        is_usable = cfg["usable"]
        ndvi_mean = cfg["ndvi"]

        frame_assets: list[AssetResponse] = []

        if is_usable:
            # Generate actual PNG assets for RGB and NDVI
            for layer in ["rgb", "ndvi"]:
                png_bytes = _generate_field_texture(256, 256, layer, ndvi_mean)
                sha256_hash = hashlib.sha256(png_bytes).hexdigest()
                file_name = f"{frame_id}_{layer}.png"
                (assets_dir / file_name).write_bytes(png_bytes)

                asset_id = uuid4()
                url = f"/v1/fields/{field_id}/timelapses/{ds_id}/frames/{frame_id}/assets/{layer}"
                frame_assets.append(
                    AssetResponse(
                        id=asset_id,
                        layer=layer,  # type: ignore[arg-type]
                        url=url,
                        width=256,
                        height=256,
                        bbox=[-64.2, -32.9, -64.1, -32.8],
                        crs="EPSG:4326",
                        sha256=sha256_hash,
                    )
                )

        frames.append(
            TimelapseFrame(
                id=frame_id,
                observed_at=datetime.combine(obs_date, datetime.min.time(), tzinfo=timezone.utc),
                local_date=obs_date,
                source_item_ids=[f"S2A_MSIL2A_DEMO_{obs_date.isoformat()}"],
                usable=is_usable,
                valid_area_fraction=cfg["valid_frac"],
                valid_pixel_count=int(cfg["valid_frac"] * 2450),
                ndvi=NdviMetrics(
                    mean=ndvi_mean if is_usable else None,
                    p10=round(ndvi_mean * 0.85, 2) if is_usable else None,
                    p90=round(min(1.0, ndvi_mean * 1.12), 2) if is_usable else None,
                ),
                missing_reason=cfg["reason"],
                available_layers=["rgb", "ndvi"] if is_usable else [],
                assets=frame_assets,
            )
        )

    sources = [
        TimelapseSource(
            id="terria-synthetic-crop-engine",
            provider="TERRIA Synthetic Demo Engine",
            dataset="Simulated Sentinel-2 L2A & Weather Timeline",
            model="Crop Phenology Demo Model v1",
            resolution="Synthetic 10m Ground Sample Distance",
            retrieved_at=now_utc,
            documentation_url="https://terria.ag/docs/demo-dataset",
            attribution="Synthetic demonstration data for visual and slider validation only.",
        ),
        TimelapseSource(
            id="synthetic-weather-engine",
            provider="TERRIA Weather Simulator",
            dataset="Simulated ERA5 Historical Weather Daily Series",
            model="Regional Microclimate Approximation",
            resolution="Field Centroid Daily",
            retrieved_at=now_utc,
            documentation_url="https://terria.ag/docs/demo-dataset",
            attribution="Simulated weather records for UI testing.",
        ),
    ]

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
        status="ready",
        generated_at=now_utc,
        is_demo=True,
        playback=PlaybackConfig(max_image_age_days=settings.timelapse_max_image_age_days, step_days=1),
        frames=frames,
        weather_daily=weather_daily,
        sources=sources,
        missing_reasons=[],
    )
