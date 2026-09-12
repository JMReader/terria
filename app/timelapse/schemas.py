from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas import PolygonGeometry, StrictModel


class NdviMetrics(StrictModel):
    mean: float | None = None
    p10: float | None = None
    p90: float | None = None


class FrameQuality(StrictModel):
    valid_area_fraction: float = Field(ge=0.0, le=1.0)
    valid_pixel_count: int = Field(ge=0)


class AssetResponse(StrictModel):
    id: UUID
    layer: Literal["rgb", "ndvi"]
    url: str
    width: int
    height: int
    bbox: list[float] | None = None
    crs: str | None = "EPSG:4326"
    sha256: str | None = None


class TimelapseFrame(StrictModel):
    id: UUID
    observed_at: datetime
    local_date: date
    source_item_ids: list[str] = []
    usable: bool
    valid_area_fraction: float = Field(ge=0.0, le=1.0)
    valid_pixel_count: int = Field(default=0, ge=0)
    ndvi: NdviMetrics = Field(default_factory=NdviMetrics)
    missing_reason: str | None = None
    available_layers: list[str] = ["rgb", "ndvi"]
    assets: list[AssetResponse] = []


class WeatherDaily(StrictModel):
    date: date
    precipitation_mm: float | None = None
    precipitation_7d_mm: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    source_id: str = "open-meteo-era5"
    missing_reason: str | None = None


class TimelapseSource(StrictModel):
    id: str
    provider: str
    dataset: str
    model: str | None = None
    resolution: str | None = None
    retrieved_at: datetime
    documentation_url: str
    attribution: str


class PlaybackConfig(StrictModel):
    max_image_age_days: int = 10
    step_days: int = 1


class TimelapseManifest(StrictModel):
    dataset_id: UUID
    schema_version: Literal["1"] = "1"
    processing_version: str
    field_id: UUID
    geometry_version_id: UUID
    boundary: PolygonGeometry
    area_hectares: float
    start_date: date
    end_date: date
    timezone: str = "America/Argentina/Cordoba"
    status: Literal["ready", "partial", "failed"]
    generated_at: datetime
    is_demo: bool = False
    playback: PlaybackConfig = Field(default_factory=PlaybackConfig)
    frames: list[TimelapseFrame] = []
    weather_daily: list[WeatherDaily] = []
    sources: list[TimelapseSource] = []
    missing_reasons: list[str] = []


class PublicTimelapseManifest(StrictModel):
    dataset_id: UUID
    schema_version: Literal["1"] = "1"
    processing_version: str
    geometry_version_id: UUID
    boundary: PolygonGeometry
    area_hectares: float
    start_date: date
    end_date: date
    timezone: str = "America/Argentina/Cordoba"
    status: Literal["ready", "partial", "failed"]
    generated_at: datetime
    is_demo: bool = False
    playback: PlaybackConfig = Field(default_factory=PlaybackConfig)
    frames: list[TimelapseFrame] = []
    weather_daily: list[WeatherDaily] = []
    sources: list[TimelapseSource] = []
    missing_reasons: list[str] = []


class SatelliteState(StrictModel):
    frame_id: UUID
    observed_at: datetime
    age_days: int
    ndvi: NdviMetrics
    quality: FrameQuality
    assets: list[AssetResponse] = []


class WeatherState(StrictModel):
    date: date
    precipitation_mm: float | None = None
    precipitation_7d_mm: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None


class TimelineState(StrictModel):
    selected_date: date
    dataset_id: UUID
    geometry_version_id: UUID
    satellite: SatelliteState | None = None
    weather: WeatherState
    sources: list[TimelapseSource] = []
    missing_reasons: list[str] = []
    is_demo: bool = False


class TimelapseJobCreate(StrictModel):
    start_date: date
    end_date: date
    layers: list[str] = ["rgb", "ndvi"]
    is_demo: bool = False


class TimelapseJobResponse(StrictModel):
    id: UUID
    field_id: UUID
    geometry_version_id: UUID
    request_hash: str
    status: Literal["queued", "processing", "ready", "partial", "failed"]
    progress: float = Field(ge=0.0, le=1.0)
    dataset_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class TimelapseDatasetSummary(StrictModel):
    id: UUID
    field_id: UUID
    start_date: date
    end_date: date
    status: str
    is_demo: bool
    generated_at: datetime
    frames_count: int
