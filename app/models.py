"""Modelos SQLAlchemy Core sobre los schemas de dominio de Supabase.

Espejan `supabase/migrations/*_terria_initial_schema.sql` más el alignment del
backend (`*_timelapse_backend_alignment.sql`). Alembic es dueño del schema en
Postgres; estas tablas sólo describen el acceso desde la API.
"""

from __future__ import annotations

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

metadata = sa.MetaData()

_UUID = postgresql.UUID(as_uuid=True)
_TSTZ = sa.DateTime(timezone=True)
_JSONB = postgresql.JSONB

profiles = sa.Table(
    "profiles",
    metadata,
    sa.Column("id", _UUID, primary_key=True),
    sa.Column("display_name", sa.Text),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    schema="core",
)

fields = sa.Table(
    "fields",
    metadata,
    sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("owner_id", _UUID, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("boundary", Geography("MULTIPOLYGON", srid=4326), nullable=False),
    sa.Column("centroid", Geography("POINT", srid=4326)),
    sa.Column("area_hectares", sa.Numeric(12, 2), nullable=False),
    sa.Column("country", sa.String(2), server_default="AR"),
    sa.Column("province", sa.Text),
    sa.Column("locality", sa.Text),
    sa.Column("visibility", sa.Text, server_default="private"),
    sa.Column("public_slug", sa.Text),
    sa.Column("archived_at", _TSTZ),
    sa.Column("published_at", _TSTZ),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    sa.Column("updated_at", _TSTZ, server_default=sa.text("now()")),
    schema="core",
)

audit_log = sa.Table(
    "audit_log",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
    sa.Column("field_id", _UUID),
    sa.Column("actor_id", _UUID),
    sa.Column("action", sa.Text, nullable=False),
    sa.Column("metadata", _JSONB, server_default=sa.text("'{}'::jsonb")),
    sa.Column("occurred_at", _TSTZ, server_default=sa.text("now()")),
    schema="core",
)

geometry_versions = sa.Table(
    "geometry_versions",
    metadata,
    sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("field_id", _UUID, nullable=False),
    sa.Column("boundary", Geography("MULTIPOLYGON", srid=4326), nullable=False),
    sa.Column("geometry_hash", sa.Text, nullable=False),
    sa.Column("area_hectares", sa.Numeric(12, 2), nullable=False),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    sa.UniqueConstraint("field_id", "geometry_hash", name="geometry_versions_field_hash_uq"),
    schema="timelapse",
)

datasets = sa.Table(
    "datasets",
    metadata,
    sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("field_id", _UUID, nullable=False),
    sa.Column("requested_by", _UUID),
    sa.Column("source_mode", sa.Text, nullable=False),
    sa.Column("is_demo", sa.Boolean, server_default=sa.text("false")),
    sa.Column("date_from", sa.Date),
    sa.Column("date_to", sa.Date),
    sa.Column("status", sa.Text, server_default="queued"),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("manifest", _JSONB),
    sa.Column("is_public", sa.Boolean, server_default=sa.text("false")),
    sa.Column("public_slug", sa.Text),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    schema="timelapse",
)

frames = sa.Table(
    "frames",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
    sa.Column("dataset_id", _UUID, nullable=False),
    sa.Column("frame_date", sa.Date, nullable=False),
    sa.Column("weather", _JSONB),
    sa.Column("satellite", _JSONB),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    schema="timelapse",
)

assets = sa.Table(
    "assets",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
    sa.Column("frame_id", sa.BigInteger, nullable=False),
    sa.Column("layer", sa.Text, nullable=False),
    sa.Column("storage_ref", sa.Text, nullable=False),
    sa.Column("mime", sa.Text),
    sa.Column("byte_size", sa.BigInteger),
    schema="timelapse",
)

publications = sa.Table(
    "publications",
    metadata,
    sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("dataset_id", _UUID, nullable=False),
    sa.Column("public_slug", sa.Text, nullable=False),
    sa.Column("published_at", _TSTZ, server_default=sa.text("now()")),
    sa.Column("unpublished_at", _TSTZ),
    schema="timelapse",
)

jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("kind", sa.Text, nullable=False),
    sa.Column("ref_id", _UUID, nullable=False),
    sa.Column("state", sa.Text, server_default="queued"),
    sa.Column("attempts", sa.Integer, server_default=sa.text("0")),
    sa.Column("lease_until", _TSTZ),
    sa.Column("lease_token", sa.Text),
    sa.Column("progress", sa.Numeric(4, 3), server_default=sa.text("0")),
    sa.Column("payload", _JSONB, server_default=sa.text("'{}'::jsonb")),
    sa.Column("last_error", sa.Text),
    sa.Column("not_before", _TSTZ),
    sa.Column("created_at", _TSTZ, server_default=sa.text("now()")),
    sa.Column("updated_at", _TSTZ, server_default=sa.text("now()")),
    schema="ops",
)


def multipolygon_geography(geojson: str):
    """Expresión PostGIS: GeoJSON → geography(MULTIPOLYGON, 4326)."""
    return sa.cast(
        sa.func.ST_Multi(sa.func.ST_GeomFromGeoJSON(geojson)),
        Geography("MULTIPOLYGON", srid=4326),
    )


def boundary_geojson_expr():
    """Expresión para leer `core.fields.boundary` como texto GeoJSON."""
    return sa.func.ST_AsGeoJSON(fields.c.boundary)
