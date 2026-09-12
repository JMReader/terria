from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from app.config import settings
from app.schemas import FieldCreate, FieldResponse, FieldUpdate, PolygonGeometry, utcnow
from app.timelapse.repository import timelapse_repository


class FieldNotFound(Exception):
    pass


def polygon_area_hectares(boundary: PolygonGeometry | dict) -> float:
    """Approximate planar area for development; PostGIS is authoritative in Supabase."""
    if isinstance(boundary, dict):
        coords = boundary.get("coordinates", [])
    else:
        coords = boundary.coordinates
    if not coords or not coords[0]:
        return 0.0
    ring = coords[0]
    area = sum(
        ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    )
    return round(abs(area) * 6_160.0, 2)


@dataclass
class StoredField:
    value: FieldResponse
    published_at: object | None = None


class SQLiteFieldStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = str(settings.db_file_path)
        else:
            self.db_path = str(db_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS fields (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                boundary TEXT NOT NULL,
                area_hectares REAL NOT NULL,
                country TEXT,
                province TEXT,
                locality TEXT,
                visibility TEXT NOT NULL DEFAULT 'private',
                public_slug TEXT UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            );
            """)

    def create(self, payload: FieldCreate) -> FieldResponse:
        now = utcnow()
        field_id = uuid4()
        area_ha = polygon_area_hectares(payload.boundary)

        field = FieldResponse(
            id=field_id,
            name=payload.name,
            description=payload.description,
            boundary=payload.boundary,
            area_hectares=area_ha,
            country=payload.country,
            province=payload.province,
            locality=payload.locality,
            visibility="private",
            public_slug=None,
            created_at=now,
            updated_at=now,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO fields (
                    id, name, description, boundary, area_hectares, country, province,
                    locality, visibility, public_slug, created_at, updated_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(field.id),
                    field.name,
                    field.description,
                    field.boundary.model_dump_json(),
                    field.area_hectares,
                    field.country,
                    field.province,
                    field.locality,
                    field.visibility,
                    field.public_slug,
                    field.created_at.isoformat(),
                    field.updated_at.isoformat(),
                    None,
                ),
            )

        # Track geometry version in timelapse repository
        timelapse_repository.get_or_create_geometry_version(
            field_id=field.id,
            boundary=field.boundary,
            area_hectares=field.area_hectares,
        )

        return field

    def list(self) -> list[FieldResponse]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM fields ORDER BY created_at DESC").fetchall()
            return [self._row_to_field(row) for row in rows]

    def get(self, field_id: UUID) -> StoredField:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM fields WHERE id = ?", (str(field_id),)).fetchone()
            if not row:
                raise FieldNotFound
            field = self._row_to_field(row)
            published_at = (
                datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
            )
            return StoredField(value=field, published_at=published_at)

    def update(self, field_id: UUID, payload: FieldUpdate) -> FieldResponse:
        stored = self.get(field_id)
        current = stored.value
        changes = payload.model_dump(exclude_unset=True)

        if "boundary" in changes:
            # Handle boundary safely whether dict or PolygonGeometry
            changes["area_hectares"] = polygon_area_hectares(changes["boundary"])
            if isinstance(changes["boundary"], dict):
                changes["boundary"] = PolygonGeometry.model_validate(changes["boundary"])

        updated_field = current.model_copy(update={**changes, "updated_at": utcnow()})

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE fields
                SET name = ?, description = ?, boundary = ?, area_hectares = ?, province = ?,
                    locality = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated_field.name,
                    updated_field.description,
                    updated_field.boundary.model_dump_json(),
                    updated_field.area_hectares,
                    updated_field.province,
                    updated_field.locality,
                    updated_field.updated_at.isoformat(),
                    str(field_id),
                ),
            )

        if "boundary" in changes:
            timelapse_repository.get_or_create_geometry_version(
                field_id=updated_field.id,
                boundary=updated_field.boundary,
                area_hectares=updated_field.area_hectares,
            )

        return updated_field

    def publish(self, field_id: UUID) -> FieldResponse:
        stored = self.get(field_id)
        slug = stored.value.public_slug or uuid4().hex[:12]
        now = utcnow()
        updated_field = stored.value.model_copy(
            update={"visibility": "public", "public_slug": slug, "updated_at": now}
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE fields
                SET visibility = 'public', public_slug = ?, updated_at = ?, published_at = ?
                WHERE id = ?
                """,
                (slug, now.isoformat(), now.isoformat(), str(field_id)),
            )
        return updated_field

    def unpublish(self, field_id: UUID) -> FieldResponse:
        stored = self.get(field_id)
        now = utcnow()
        updated_field = stored.value.model_copy(
            update={"visibility": "private", "updated_at": now}
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE fields
                SET visibility = 'private', updated_at = ?
                WHERE id = ?
                """,
                (now.isoformat(), str(field_id)),
            )
        return updated_field

    def archive(self, field_id: UUID) -> None:
        self.get(field_id)
        with self._get_connection() as conn:
            conn.execute("DELETE FROM fields WHERE id = ?", (str(field_id),))

    def get_public(self, slug: str) -> StoredField:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fields WHERE visibility = 'public' AND public_slug = ?",
                (slug,),
            ).fetchone()
            if not row:
                raise FieldNotFound
            field = self._row_to_field(row)
            published_at = (
                datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
            )
            return StoredField(value=field, published_at=published_at)

    @staticmethod
    def _row_to_field(row: sqlite3.Row) -> FieldResponse:
        return FieldResponse(
            id=UUID(row["id"]),
            name=row["name"],
            description=row["description"],
            boundary=PolygonGeometry.model_validate_json(row["boundary"]),
            area_hectares=float(row["area_hectares"]),
            country=row["country"],
            province=row["province"],
            locality=row["locality"],
            visibility=row["visibility"],
            public_slug=row["public_slug"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class InMemoryFieldStore(SQLiteFieldStore):
    """Backwards-compatible store for tests running fully in-memory."""

    def __init__(self) -> None:
        super().__init__(db_path=":memory:")
