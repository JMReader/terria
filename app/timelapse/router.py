from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.config import settings
from app.store import FieldNotFound, get_field_store
from app.timelapse.repository import timelapse_repository
from app.timelapse.schemas import (
    PublicTimelapseManifest,
    TimelapseDatasetSummary,
    TimelapseFrame,
    TimelapseJobCreate,
    TimelapseJobResponse,
    TimelapseManifest,
    TimelineState,
)
from app.timelapse.selector import compute_timeline_state

router = APIRouter()
field_store = get_field_store()


def _timelapse_not_found(request: Request, message: str = "Timelapse dataset not found") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "TIMELAPSE_NOT_FOUND",
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


def _field_not_found(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "FIELD_NOT_FOUND",
            "message": "The field was not found",
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


def _bad_request(request: Request, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": code,
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


@router.post(
    "/v1/fields/{field_id}/timelapses",
    summary="Create or queue a timelapse dataset generation job",
    tags=["Timelapse"],
)
def create_or_get_timelapse(
    field_id: UUID,
    payload: TimelapseJobCreate,
    request: Request,
    response: Response,
) -> TimelapseJobResponse | dict[str, str]:
    try:
        stored_field = field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None

    if payload.start_date > payload.end_date:
        raise _bad_request(request, "INVALID_DATE_RANGE", "start_date must be before or equal to end_date")

    period_days = (payload.end_date - payload.start_date).days + 1
    if period_days > 366:
        raise _bad_request(
            request, "PERIOD_TOO_LONG", f"Maximum requested period is 366 days (got {period_days})"
        )

    field = stored_field.value
    geom_version_id = timelapse_repository.get_or_create_geometry_version(
        field_id=field.id,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
    )

    req_hash = timelapse_repository.compute_request_hash(
        field_id=field.id,
        geometry_version_id=geom_version_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        layers=payload.layers,
        is_demo=payload.is_demo,
    )

    # 1. Reuse existing ready/partial dataset if available
    existing_dataset = timelapse_repository.find_ready_dataset_for_hash(req_hash)
    if existing_dataset:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ready",
            "dataset_id": str(existing_dataset.dataset_id),
            "message": "Dataset already generated and available",
        }

    # 2. Check active job
    active_job = timelapse_repository.find_active_job(req_hash)
    if active_job:
        response.status_code = status.HTTP_202_ACCEPTED
        return active_job

    # 3. Create job
    job = timelapse_repository.create_job(
        field_id=field.id,
        geometry_version_id=geom_version_id,
        request_hash=req_hash,
        parameters=payload.model_dump(mode="json"),
    )
    response.status_code = status.HTTP_202_ACCEPTED
    return job


@router.get(
    "/v1/timelapse-jobs/{job_id}",
    response_model=TimelapseJobResponse,
    summary="Get status of a timelapse generation job",
    tags=["Timelapse"],
)
def get_timelapse_job(job_id: UUID, request: Request) -> TimelapseJobResponse:
    job = timelapse_repository.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Timelapse job {job_id} not found",
                "request_id": request.headers.get("X-Request-ID", "local"),
            },
        )
    return job


@router.get(
    "/v1/fields/{field_id}/timelapses",
    response_model=list[TimelapseDatasetSummary],
    summary="List generated timelapse datasets for a field",
    tags=["Timelapse"],
)
def list_field_timelapses(field_id: UUID, request: Request) -> list[TimelapseDatasetSummary]:
    try:
        field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None
    return timelapse_repository.list_datasets_for_field(field_id)


@router.get(
    "/v1/fields/{field_id}/timelapses/{dataset_id}",
    response_model=TimelapseManifest,
    summary="Get private timelapse manifest",
    tags=["Timelapse"],
)
def get_timelapse_manifest(field_id: UUID, dataset_id: UUID, request: Request) -> TimelapseManifest:
    manifest = timelapse_repository.get_dataset(dataset_id)
    if not manifest or manifest.field_id != field_id:
        raise _timelapse_not_found(request)
    return manifest


@router.get(
    "/v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id}",
    response_model=TimelapseFrame,
    summary="Get details and asset URLs for a specific frame",
    tags=["Timelapse"],
)
def get_timelapse_frame(
    field_id: UUID, dataset_id: UUID, frame_id: UUID, request: Request
) -> TimelapseFrame:
    manifest = timelapse_repository.get_dataset(dataset_id)
    if not manifest or manifest.field_id != field_id:
        raise _timelapse_not_found(request)
    frame = next((f for f in manifest.frames if f.id == frame_id), None)
    if not frame:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FRAME_NOT_FOUND",
                "message": f"Frame {frame_id} not found in dataset",
                "request_id": request.headers.get("X-Request-ID", "local"),
            },
        )
    return frame


@router.get(
    "/v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id}/assets/{layer}",
    summary="Download or view RGB / NDVI asset image for a frame",
    tags=["Timelapse"],
)
def get_timelapse_frame_asset(
    field_id: UUID,
    dataset_id: UUID,
    frame_id: UUID,
    layer: Literal["rgb", "ndvi"],
    request: Request,
) -> Response:
    manifest = timelapse_repository.get_dataset(dataset_id)
    if not manifest or manifest.field_id != field_id:
        raise _timelapse_not_found(request)

    file_path = settings.assets_dir / f"{frame_id}_{layer}.png"
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ASSET_NOT_FOUND",
                "message": f"Asset {layer} for frame {frame_id} not found on disk",
                "request_id": request.headers.get("X-Request-ID", "local"),
            },
        )
    return Response(content=file_path.read_bytes(), media_type="image/png")


@router.get(
    "/v1/fields/{field_id}/timelapses/{dataset_id}/timeline-state",
    response_model=TimelineState,
    summary="Get resolved timeline state for a given date",
    tags=["Timelapse"],
)
def get_timeline_state(
    field_id: UUID,
    dataset_id: UUID,
    date_val: date = Query(alias="date"),
    request: Request = None,  # type: ignore[assignment]
) -> TimelineState:
    manifest = timelapse_repository.get_dataset(dataset_id)
    if not manifest or manifest.field_id != field_id:
        raise _timelapse_not_found(request)
    return compute_timeline_state(manifest, date_val)


@router.post(
    "/v1/fields/{field_id}/timelapses/{dataset_id}/publish",
    summary="Publish timelapse dataset for the public field passport",
    tags=["Timelapse"],
)
def publish_timelapse(field_id: UUID, dataset_id: UUID, request: Request) -> dict[str, str]:
    try:
        stored = field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None

    manifest = timelapse_repository.get_dataset(dataset_id)
    if not manifest or manifest.field_id != field_id:
        raise _timelapse_not_found(request)

    if stored.value.visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "FIELD_NOT_PUBLIC",
                "message": "The field must be published before publishing its timelapse",
                "request_id": request.headers.get("X-Request-ID", "local"),
            },
        )

    timelapse_repository.publish_dataset(field_id=field_id, dataset_id=dataset_id)
    return {
        "status": "published",
        "field_id": str(field_id),
        "dataset_id": str(dataset_id),
        "public_url": f"/v1/public/fields/{stored.value.public_slug}/timelapse",
    }


@router.get(
    "/v1/public/fields/{public_slug}/timelapse",
    response_model=PublicTimelapseManifest,
    summary="Get public timelapse manifest for a published field",
    tags=["Public fields"],
)
def get_public_timelapse(public_slug: str, request: Request) -> PublicTimelapseManifest:
    try:
        stored = field_store.get_public(public_slug)
    except FieldNotFound:
        raise _field_not_found(request) from None

    manifest = timelapse_repository.get_published_dataset_for_field(stored.value.id)
    if not manifest:
        raise _timelapse_not_found(request, "No timelapse dataset has been published for this field")

    return PublicTimelapseManifest(
        dataset_id=manifest.dataset_id,
        schema_version=manifest.schema_version,
        processing_version=manifest.processing_version,
        geometry_version_id=manifest.geometry_version_id,
        boundary=manifest.boundary,
        area_hectares=manifest.area_hectares,
        start_date=manifest.start_date,
        end_date=manifest.end_date,
        timezone=manifest.timezone,
        status=manifest.status,
        generated_at=manifest.generated_at,
        is_demo=manifest.is_demo,
        playback=manifest.playback,
        frames=manifest.frames,
        weather_daily=manifest.weather_daily,
        sources=manifest.sources,
        missing_reasons=manifest.missing_reasons,
    )


@router.get(
    "/v1/public/fields/{public_slug}/timelapse/frames/{frame_id}/assets/{layer}",
    summary="Get asset image for a published field frame",
    tags=["Public fields"],
)
def get_public_timelapse_asset(
    public_slug: str,
    frame_id: UUID,
    layer: Literal["rgb", "ndvi"],
    request: Request,
) -> Response:
    try:
        stored = field_store.get_public(public_slug)
    except FieldNotFound:
        raise _field_not_found(request) from None

    manifest = timelapse_repository.get_published_dataset_for_field(stored.value.id)
    if not manifest:
        raise _timelapse_not_found(request)

    frame = next((f for f in manifest.frames if f.id == frame_id), None)
    if not frame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")

    file_path = settings.assets_dir / f"{frame_id}_{layer}.png"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset file not found")

    return Response(content=file_path.read_bytes(), media_type="image/png")
