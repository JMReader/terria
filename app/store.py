from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator
from uuid import UUID, uuid4

import sqlalchemy as sa
from geoalchemy2 import Geography

from app.config import settings
from app.db import get_engine
from app.models import audit_log, fields as fields_table, multipolygon_geography
from app.ownership import resolve_owner_id
from app.schemas import FieldCreate, FieldResponse, FieldUpdate, PolygonGeometry, utcnow
from app.timelapse.repository import get_timelapse_repository


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

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, uri=self.db_path.startswith("file:"))
        conn.row_factory = sqlite3.Row
        if not self.db_path.startswith("file:"):
            conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._connection() as conn:
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

        with self._connection() as conn:
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
        get_timelapse_repository().get_or_create_geometry_version(
            field_id=field.id,
            boundary=field.boundary,
            area_hectares=field.area_hectares,
        )

        return field

    def list(self) -> list[FieldResponse]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM fields ORDER BY created_at DESC").fetchall()
            return [self._row_to_field(row) for row in rows]

    def get(self, field_id: UUID) -> StoredField:
        with self._connection() as conn:
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

        with self._connection() as conn:
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
            get_timelapse_repository().get_or_create_geometry_version(
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

        with self._connection() as conn:
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

        with self._connection() as conn:
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
        with self._connection() as conn:
            conn.execute("DELETE FROM fields WHERE id = ?", (str(field_id),))

    def get_public(self, slug: str) -> StoredField:
        with self._connection() as conn:
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
    """Backwards-compatible store for tests running fully in-memory.

    Usa una DB SQLite shared-cache: la conexión ancla la mantiene viva entre las
    conexiones por-operación del store.
    """

    _URI = "file:terria-mem?mode=memory&cache=shared"

    def __init__(self) -> None:
        self._anchor = sqlite3.connect(self._URI, uri=True)
        super().__init__(db_path=self._URI)


class PostgresFieldStore:
    """Persistencia de fields sobre `core.fields` (Supabase Postgres + PostGIS).

    La superficie y el centroide se calculan en la base (`ST_Area`/`ST_Centroid`
    sobre geography). El borrado es lógico (`archived_at`) y cada escritura deja
    rastro en `core.audit_log`. Cumple el mismo contrato que `SQLiteFieldStore`.
    """

    _COLUMNS = (
        fields_table.c.id,
        fields_table.c.name,
        fields_table.c.description,
        sa.func.ST_AsGeoJSON(fields_table.c.boundary).label("boundary_geojson"),
        fields_table.c.area_hectares,
        fields_table.c.country,
        fields_table.c.province,
        fields_table.c.locality,
        fields_table.c.visibility,
        fields_table.c.public_slug,
        fields_table.c.published_at,
        fields_table.c.created_at,
        fields_table.c.updated_at,
    )

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _audit(conn: sa.Connection, field_id: UUID, action: str, meta: dict[str, Any]) -> None:
        conn.execute(
            audit_log.insert().values(field_id=field_id, action=action, metadata=meta)
        )

    def _select(self) -> sa.Select:
        return sa.select(*self._COLUMNS).where(fields_table.c.archived_at.is_(None))

    def _fetch_row(self, conn: sa.Connection, field_id: UUID):
        row = conn.execute(
            self._select().where(fields_table.c.id == field_id)
        ).mappings().first()
        if row is None:
            raise FieldNotFound
        return row

    @staticmethod
    def _row_to_field(row: Any) -> FieldResponse:
        geojson = json.loads(row["boundary_geojson"])
        coordinates = (
            geojson["coordinates"][0]
            if geojson["type"] == "MultiPolygon"
            else geojson["coordinates"]
        )
        return FieldResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            boundary=PolygonGeometry(type="Polygon", coordinates=coordinates),
            area_hectares=float(row["area_hectares"]),
            country=row["country"],
            province=row["province"],
            locality=row["locality"],
            visibility=row["visibility"],
            public_slug=row["public_slug"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ── API pública (mismo contrato que SQLiteFieldStore) ───────────────────

    def create(self, payload: FieldCreate) -> FieldResponse:
        geom = multipolygon_geography(payload.boundary.model_dump_json())
        stmt = (
            fields_table.insert()
            .values(
                owner_id=resolve_owner_id(),
                name=payload.name,
                description=payload.description,
                boundary=geom,
                centroid=sa.cast(
                    sa.func.ST_Centroid(geom), Geography("POINT", srid=4326)
                ),
                area_hectares=sa.cast(
                    sa.func.ST_Area(geom) / 10000.0, sa.Numeric(12, 2)
                ),
                country=payload.country or "AR",
                province=payload.province,
                locality=payload.locality,
            )
            .returning(fields_table.c.id)
        )
        with get_engine().begin() as conn:
            field_id = conn.execute(stmt).scalar_one()
            self._audit(conn, field_id, "field.created", {"name": payload.name})

        field = self.get(field_id).value
        get_timelapse_repository().get_or_create_geometry_version(
            field_id=field.id,
            boundary=field.boundary,
            area_hectares=field.area_hectares,
        )
        return field

    def list(self) -> list[FieldResponse]:
        with get_engine().connect() as conn:
            rows = conn.execute(
                self._select().order_by(fields_table.c.created_at.desc())
            ).mappings().all()
            return [self._row_to_field(row) for row in rows]

    def get(self, field_id: UUID) -> StoredField:
        with get_engine().connect() as conn:
            row = self._fetch_row(conn, field_id)
            return StoredField(
                value=self._row_to_field(row), published_at=row["published_at"]
            )

    def update(self, field_id: UUID, payload: FieldUpdate) -> FieldResponse:
        changes = payload.model_dump(exclude_unset=True)

        assignments: dict[str, Any] = {}
        for key in ("name", "description", "province", "locality"):
            if key in changes:
                assignments[key] = changes[key]

        if "boundary" in changes:
            boundary = changes["boundary"]
            if isinstance(boundary, dict):
                boundary = PolygonGeometry.model_validate(boundary)
            geom = multipolygon_geography(boundary.model_dump_json())
            assignments["boundary"] = geom
            assignments["centroid"] = sa.cast(
                sa.func.ST_Centroid(geom), Geography("POINT", srid=4326)
            )
            assignments["area_hectares"] = sa.cast(
                sa.func.ST_Area(geom) / 10000.0, sa.Numeric(12, 2)
            )

        with get_engine().begin() as conn:
            self._fetch_row(conn, field_id)
            if assignments:
                conn.execute(
                    fields_table.update()
                    .where(fields_table.c.id == field_id)
                    .values(**assignments)
                )
            self._audit(conn, field_id, "field.updated", {"fields": sorted(changes)})

        field = self.get(field_id).value
        if "boundary" in changes:
            get_timelapse_repository().get_or_create_geometry_version(
                field_id=field.id,
                boundary=field.boundary,
                area_hectares=field.area_hectares,
            )
        return field

    def publish(self, field_id: UUID) -> FieldResponse:
        with get_engine().begin() as conn:
            row = self._fetch_row(conn, field_id)
            slug = row["public_slug"] or uuid4().hex[:12]
            conn.execute(
                fields_table.update()
                .where(fields_table.c.id == field_id)
                .values(
                    visibility="public",
                    public_slug=slug,
                    published_at=sa.func.coalesce(
                        fields_table.c.published_at, sa.func.now()
                    ),
                )
            )
            self._audit(conn, field_id, "field.published", {"public_slug": slug})
        return self.get(field_id).value

    def unpublish(self, field_id: UUID) -> FieldResponse:
        with get_engine().begin() as conn:
            self._fetch_row(conn, field_id)
            conn.execute(
                fields_table.update()
                .where(fields_table.c.id == field_id)
                .values(visibility="private", public_slug=None)
            )
            self._audit(conn, field_id, "field.unpublished", {})
        return self.get(field_id).value

    def archive(self, field_id: UUID) -> None:
        with get_engine().begin() as conn:
            self._fetch_row(conn, field_id)
            conn.execute(
                fields_table.update()
                .where(fields_table.c.id == field_id)
                .values(archived_at=sa.func.now(), visibility="private", public_slug=None)
            )
            self._audit(conn, field_id, "field.archived", {})

    def get_public(self, slug: str) -> StoredField:
        with get_engine().connect() as conn:
            row = conn.execute(
                self._select().where(
                    fields_table.c.public_slug == slug,
                    fields_table.c.visibility == "public",
                )
            ).mappings().first()
            if row is None:
                raise FieldNotFound
            return StoredField(
                value=self._row_to_field(row), published_at=row["published_at"]
            )


def get_field_store() -> SQLiteFieldStore | PostgresFieldStore:
    """Selecciona el backend de persistencia según la configuración.

    `DATABASE_URL` presente → Supabase Postgres (`core.fields`); si no, SQLite
    local para desarrollo y tests.
    """
    if settings.use_supabase:
        return PostgresFieldStore()
    return SQLiteFieldStore()
