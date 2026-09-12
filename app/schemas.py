from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Position = Annotated[list[float], Field(min_length=2, max_length=3)]


class PolygonGeometry(StrictModel):
    type: Literal["Polygon"]
    coordinates: list[list[Position]]

    @field_validator("coordinates")
    @classmethod
    def requires_a_closed_ring(cls, rings: list[list[Position]]) -> list[list[Position]]:
        if not rings or len(rings[0]) < 4 or rings[0][0] != rings[0][-1]:
            raise ValueError("A polygon requires a closed outer ring with at least four positions")
        for position in rings[0]:
            longitude, latitude = position[:2]
            if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                raise ValueError("Coordinates must be valid WGS84 longitude/latitude values")
        return rings


class FieldCreate(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str | None, Field(max_length=2_000)] = None
    boundary: PolygonGeometry
    country: Annotated[str | None, Field(max_length=2)] = "AR"
    province: Annotated[str | None, Field(max_length=100)] = None
    locality: Annotated[str | None, Field(max_length=100)] = None


class FieldUpdate(StrictModel):
    name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    description: Annotated[str | None, Field(max_length=2_000)] = None
    boundary: PolygonGeometry | None = None
    province: Annotated[str | None, Field(max_length=100)] = None
    locality: Annotated[str | None, Field(max_length=100)] = None


class FieldResponse(StrictModel):
    id: UUID
    name: str
    description: str | None
    boundary: PolygonGeometry
    area_hectares: float
    country: str | None
    province: str | None
    locality: str | None
    visibility: Literal["private", "public"]
    public_slug: str | None
    created_at: datetime
    updated_at: datetime


class PublicFieldResponse(StrictModel):
    name: str
    description: str | None
    boundary: PolygonGeometry
    area_hectares: float
    country: str | None
    province: str | None
    locality: str | None
    published_at: datetime


class PublishResponse(StrictModel):
    public_slug: str
    public_url: str


class ErrorBody(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorBody


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
