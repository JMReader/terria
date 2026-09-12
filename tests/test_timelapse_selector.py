from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4


from app.schemas import PolygonGeometry
from app.timelapse.providers.weather import calculate_7d_precipitation
from app.timelapse.schemas import (
    NdviMetrics,
    PlaybackConfig,
    TimelapseFrame,
    TimelapseManifest,
    TimelapseSource,
    WeatherDaily,
)
from app.timelapse.selector import compute_timeline_state


def create_sample_manifest(
    max_age_days: int = 10,
    frames: list[TimelapseFrame] | None = None,
    weather: list[WeatherDaily] | None = None,
) -> TimelapseManifest:
    boundary = PolygonGeometry(
        type="Polygon",
        coordinates=[[[-64.2, -32.9], [-64.1, -32.9], [-64.1, -32.8], [-64.2, -32.9]]],
    )
    return TimelapseManifest(
        dataset_id=uuid4(),
        schema_version="1",
        processing_version="0.1.0",
        field_id=uuid4(),
        geometry_version_id=uuid4(),
        boundary=boundary,
        area_hectares=150.0,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        timezone="America/Argentina/Cordoba",
        status="ready",
        generated_at=datetime.now(timezone.utc),
        is_demo=True,
        playback=PlaybackConfig(max_image_age_days=max_age_days, step_days=1),
        frames=frames or [],
        weather_daily=weather or [],
        sources=[
            TimelapseSource(
                id="test-src",
                provider="TestProvider",
                dataset="TestDataset",
                retrieved_at=datetime.now(timezone.utc),
                documentation_url="https://test.local",
                attribution="Test attribution",
            )
        ],
        missing_reasons=[],
    )


def test_date_prior_to_first_satellite_capture() -> None:
    """When selected_date is before the first observation, satellite must be null."""
    frame = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 10, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 10),
        usable=True,
        valid_area_fraction=0.95,
        valid_pixel_count=1000,
        ndvi=NdviMetrics(mean=0.65, p10=0.55, p90=0.75),
    )
    weather = [
        WeatherDaily(date=date(2024, 1, 5), precipitation_mm=0.0, precipitation_7d_mm=0.0)
    ]
    manifest = create_sample_manifest(frames=[frame], weather=weather)

    state = compute_timeline_state(manifest, date(2024, 1, 5))

    assert state.satellite is None
    assert any("NO_SATELLITE_OBSERVATION" in reason for reason in state.missing_reasons)
    assert state.weather.date == date(2024, 1, 5)
    assert state.weather.precipitation_mm == 0.0


def test_satellite_max_age_limit_exceeded() -> None:
    """If age exceeds max_image_age_days (e.g. 10 days), satellite must be null with MAX_IMAGE_AGE_EXCEEDED."""
    frame = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 2, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 2),
        usable=True,
        valid_area_fraction=0.90,
        valid_pixel_count=900,
        ndvi=NdviMetrics(mean=0.50, p10=0.40, p90=0.60),
    )
    manifest = create_sample_manifest(max_age_days=10, frames=[frame])

    # Day 10 after Jan 2 is Jan 12 (age = 10, within limit)
    state_day_10 = compute_timeline_state(manifest, date(2024, 1, 12))
    assert state_day_10.satellite is not None
    assert state_day_10.satellite.age_days == 10

    # Day 11 after Jan 2 is Jan 13 (age = 11, strictly exceeds limit 10)
    state_day_11 = compute_timeline_state(manifest, date(2024, 1, 13))
    assert state_day_11.satellite is None
    assert any("MAX_IMAGE_AGE_EXCEEDED" in reason for reason in state_day_11.missing_reasons)


def test_no_future_captures_used() -> None:
    """An observation in the future relative to selected_date must never be used."""
    frame_past = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 5, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 5),
        usable=True,
        valid_area_fraction=0.92,
        valid_pixel_count=920,
        ndvi=NdviMetrics(mean=0.42),
    )
    frame_future = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 15),
        usable=True,
        valid_area_fraction=0.98,
        valid_pixel_count=980,
        ndvi=NdviMetrics(mean=0.75),
    )
    manifest = create_sample_manifest(frames=[frame_past, frame_future])

    state = compute_timeline_state(manifest, date(2024, 1, 10))
    assert state.satellite is not None
    assert state.satellite.frame_id == frame_past.id
    assert state.satellite.ndvi.mean == 0.42
    assert state.satellite.age_days == 5


def test_unusable_cloudy_frames_ignored() -> None:
    """Cloudy or unusable frames (usable=False) must not be selected as active texture."""
    frame_usable_old = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 2, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 2),
        usable=True,
        valid_area_fraction=0.88,
        valid_pixel_count=880,
        ndvi=NdviMetrics(mean=0.35),
    )
    frame_cloudy = TimelapseFrame(
        id=uuid4(),
        observed_at=datetime(2024, 1, 6, 14, 0, tzinfo=timezone.utc),
        local_date=date(2024, 1, 6),
        usable=False,
        valid_area_fraction=0.25,
        valid_pixel_count=250,
        missing_reason="CLOUDY_SCENE",
    )
    manifest = create_sample_manifest(frames=[frame_usable_old, frame_cloudy])

    state = compute_timeline_state(manifest, date(2024, 1, 7))
    assert state.satellite is not None
    assert state.satellite.frame_id == frame_usable_old.id
    assert state.satellite.age_days == 5


def test_zero_precipitation_vs_null_precipitation() -> None:
    """0.0 mm of rain is a valid measurement and must not be treated as null/falsy."""
    weather = [
        WeatherDaily(
            date=date(2024, 1, 1),
            precipitation_mm=0.0,
            precipitation_7d_mm=0.0,
            temperature_min_c=15.0,
            temperature_max_c=30.0,
        ),
        WeatherDaily(
            date=date(2024, 1, 2),
            precipitation_mm=None,
            precipitation_7d_mm=None,
            missing_reason="SENSOR_OFFLINE",
        ),
    ]
    manifest = create_sample_manifest(weather=weather)

    state_zero = compute_timeline_state(manifest, date(2024, 1, 1))
    assert state_zero.weather.precipitation_mm == 0.0
    assert state_zero.weather.precipitation_mm is not None

    state_null = compute_timeline_state(manifest, date(2024, 1, 2))
    assert state_null.weather.precipitation_mm is None
    assert any("WEATHER_SENSOR_OFFLINE" in r for r in state_null.missing_reasons)


def test_calculate_7d_precipitation_complete_vs_incomplete() -> None:
    """Rolling 7-day precipitation calculation:

    - When all 7 days (D-6 to D) are present, returns exact sum (even if 0.0).
    - When any day is missing or None, returns None and INCOMPLETE_7D_WINDOW.
    """
    target = date(2024, 1, 7)

    # 1. Complete with zeroes
    daily_zeros = {date(2024, 1, i): 0.0 for i in range(1, 8)}
    val, reason = calculate_7d_precipitation(daily_zeros, target)
    assert val == 0.0
    assert reason is None

    # 2. Complete with rain events: 10 + 0 + 5 + 0 + 0 + 2.5 + 0 = 17.5
    daily_rain = {
        date(2024, 1, 1): 10.0,
        date(2024, 1, 2): 0.0,
        date(2024, 1, 3): 5.0,
        date(2024, 1, 4): 0.0,
        date(2024, 1, 5): 0.0,
        date(2024, 1, 6): 2.5,
        date(2024, 1, 7): 0.0,
    }
    val, reason = calculate_7d_precipitation(daily_rain, target)
    assert val == 17.5
    assert reason is None

    # 3. Incomplete: day 3 is missing completely
    daily_missing = {
        date(2024, 1, 1): 10.0,
        date(2024, 1, 2): 0.0,
        # day 3 missing
        date(2024, 1, 4): 0.0,
        date(2024, 1, 5): 0.0,
        date(2024, 1, 6): 2.5,
        date(2024, 1, 7): 0.0,
    }
    val, reason = calculate_7d_precipitation(daily_missing, target)
    assert val is None
    assert reason == "INCOMPLETE_7D_WINDOW"

    # 4. Incomplete: day 5 is None
    daily_with_none = dict(daily_rain)
    daily_with_none[date(2024, 1, 5)] = None
    val, reason = calculate_7d_precipitation(daily_with_none, target)
    assert val is None
    assert reason == "INCOMPLETE_7D_WINDOW"
