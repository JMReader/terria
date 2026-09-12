from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.schemas import (
    FieldCreate,
    FieldResponse,
    FieldUpdate,
    PublicFieldResponse,
    PublishResponse,
)
from app.store import FieldNotFound, SQLiteFieldStore
from app.timelapse.router import router as timelapse_router
from app.valuation.router import router as valuation_router
from app.what_if.router import router as what_if_router

app = FastAPI(
    title="TERRIA API",
    summary="Backend for the shareable history of a field.",
    description="Initial CRUD API for fields, public field passports, timelapse engine, What-If simulations, and 5-year land valuation projector.",
    version="0.1.0",
    openapi_version="3.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service status."},
        {"name": "Fields", "description": "Private field management."},
        {"name": "Public fields", "description": "Shareable field passports."},
        {"name": "Timelapse", "description": "Field history and temporal observations."},
        {"name": "Simulations", "description": "What-If crop rotation and retrospective agronomic simulations."},
        {"name": "Valuation", "description": "5-year land valuation projector (FinTech & Real Estate)."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
store = SQLiteFieldStore()
app.include_router(timelapse_router)
app.include_router(what_if_router)
app.include_router(valuation_router)

DEBUG_TIMELAPSE_HTML_PATH = Path(__file__).parent / "static" / "timelapse" / "index.html"


@app.get("/debug/timelapse", response_class=HTMLResponse, tags=["Health"])
def debug_timelapse_page() -> str:
    if not DEBUG_TIMELAPSE_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Debug timelapse UI not found")
    return DEBUG_TIMELAPSE_HTML_PATH.read_text(encoding="utf-8")




def not_found(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "FIELD_NOT_FOUND",
            "message": "The field was not found",
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED, tags=["Fields"])
def create_field(payload: FieldCreate) -> FieldResponse:
    return store.create(payload)


@app.get("/v1/fields", response_model=list[FieldResponse], tags=["Fields"])
def list_fields() -> list[FieldResponse]:
    return store.list()


@app.get("/v1/fields/{field_id}", response_model=FieldResponse, tags=["Fields"])
def get_field(field_id: UUID, request: Request) -> FieldResponse:
    try:
        return store.get(field_id).value
    except FieldNotFound:
        raise not_found(request) from None


@app.patch("/v1/fields/{field_id}", response_model=FieldResponse, tags=["Fields"])
def update_field(field_id: UUID, payload: FieldUpdate, request: Request) -> FieldResponse:
    try:
        return store.update(field_id, payload)
    except FieldNotFound:
        raise not_found(request) from None


@app.post("/v1/fields/{field_id}/publish", response_model=PublishResponse, tags=["Fields"])
def publish_field(field_id: UUID, request: Request) -> PublishResponse:
    try:
        field = store.publish(field_id)
    except FieldNotFound:
        raise not_found(request) from None
    return PublishResponse(public_slug=field.public_slug or "", public_url=f"/v1/public/fields/{field.public_slug}")


@app.post("/v1/fields/{field_id}/unpublish", response_model=FieldResponse, tags=["Fields"])
def unpublish_field(field_id: UUID, request: Request) -> FieldResponse:
    try:
        return store.unpublish(field_id)
    except FieldNotFound:
        raise not_found(request) from None


@app.delete("/v1/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Fields"])
def archive_field(field_id: UUID, request: Request) -> Response:
    try:
        store.archive(field_id)
    except FieldNotFound:
        raise not_found(request) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/public/fields/{public_slug}", response_model=PublicFieldResponse, tags=["Public fields"])
def get_public_field(public_slug: str, request: Request) -> PublicFieldResponse:
    try:
        stored = store.get_public(public_slug)
    except FieldNotFound:
        raise not_found(request) from None
    field = stored.value
    return PublicFieldResponse(
        name=field.name,
        description=field.description,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
        country=field.country,
        province=field.province,
        locality=field.locality,
        published_at=stored.published_at or field.updated_at,
    )
