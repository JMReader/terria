from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.schemas import FieldCreate, FieldResponse, FieldUpdate, PolygonGeometry, utcnow


class FieldNotFound(Exception):
    pass


def polygon_area_hectares(boundary: PolygonGeometry) -> float:
    """Approximate planar area for development; PostGIS is authoritative in Supabase."""
    ring = boundary.coordinates[0]
    area = sum(
        ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    )
    return round(abs(area) * 6_160.0, 2)


@dataclass
class StoredField:
    value: FieldResponse
    published_at: object | None = None


class InMemoryFieldStore:
    def __init__(self) -> None:
        self._fields: dict[UUID, StoredField] = {}

    def create(self, payload: FieldCreate) -> FieldResponse:
        now = utcnow()
        field = FieldResponse(
            id=uuid4(),
            name=payload.name,
            description=payload.description,
            boundary=payload.boundary,
            area_hectares=polygon_area_hectares(payload.boundary),
            country=payload.country,
            province=payload.province,
            locality=payload.locality,
            visibility="private",
            public_slug=None,
            created_at=now,
            updated_at=now,
        )
        self._fields[field.id] = StoredField(value=field)
        return field

    def list(self) -> list[FieldResponse]:
        return [stored.value for stored in self._fields.values()]

    def get(self, field_id: UUID) -> StoredField:
        try:
            return self._fields[field_id]
        except KeyError as error:
            raise FieldNotFound from error

    def update(self, field_id: UUID, payload: FieldUpdate) -> FieldResponse:
        stored = self.get(field_id)
        current = stored.value
        changes = payload.model_dump(exclude_unset=True)
        if "boundary" in changes:
            changes["area_hectares"] = polygon_area_hectares(changes["boundary"])
        stored.value = current.model_copy(update={**changes, "updated_at": utcnow()})
        return stored.value

    def publish(self, field_id: UUID) -> FieldResponse:
        stored = self.get(field_id)
        slug = stored.value.public_slug or uuid4().hex[:12]
        stored.value = stored.value.model_copy(
            update={"visibility": "public", "public_slug": slug, "updated_at": utcnow()}
        )
        stored.published_at = utcnow()
        return stored.value

    def unpublish(self, field_id: UUID) -> FieldResponse:
        stored = self.get(field_id)
        stored.value = stored.value.model_copy(
            update={"visibility": "private", "updated_at": utcnow()}
        )
        return stored.value

    def archive(self, field_id: UUID) -> None:
        self.get(field_id)
        del self._fields[field_id]

    def get_public(self, slug: str) -> StoredField:
        for stored in self._fields.values():
            if stored.value.visibility == "public" and stored.value.public_slug == slug:
                return stored
        raise FieldNotFound
