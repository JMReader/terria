"""Tests de integración contra Supabase real.

Opt-in: no corren en el `pytest` normal. Para ejecutarlos:

    TERRIA_TEST_SUPABASE=1 uv run pytest tests/test_supabase_backend.py

Leen las credenciales reales desde `.env` (conftest limpia las env vars, por eso
se parsea el archivo directamente). Escriben y limpian datos de prueba en la
base compartida.
"""

from __future__ import annotations

from datetime import date
import os
from uuid import uuid4

import pytest
from dotenv import dotenv_values

if os.environ.get("TERRIA_TEST_SUPABASE") != "1":
    pytest.skip("TERRIA_TEST_SUPABASE=1 requerido", allow_module_level=True)

_env = dotenv_values(".env")
if not _env.get("DATABASE_URL"):
    pytest.skip("DATABASE_URL no configurada en .env", allow_module_level=True)

import app.db as db_module  # noqa: E402
from app.config import settings  # noqa: E402
from app.schemas import FieldCreate, PolygonGeometry  # noqa: E402
from app.store import FieldNotFound, PostgresFieldStore  # noqa: E402
from app.timelapse.repository import PostgresTimelapseRepository  # noqa: E402

settings.database_url = _env["DATABASE_URL"]
settings.database_direct_url = _env.get("DATABASE_DIRECT_URL") or None
settings.supabase_url = _env.get("SUPABASE_URL") or None
settings.supabase_service_role_key = _env.get("SUPABASE_SERVICE_ROLE_KEY") or None
settings.terria_default_owner_id = _env.get("TERRIA_DEFAULT_OWNER_ID") or None
db_module.reset_engine()

BOUNDARY = PolygonGeometry(
    type="Polygon",
    coordinates=[
        [
            [-64.20, -32.90],
            [-64.10, -32.90],
            [-64.10, -32.80],
            [-64.20, -32.80],
            [-64.20, -32.90],
        ]
    ],
)


def test_fields_crud_against_supabase() -> None:
    store = PostgresFieldStore()
    field = store.create(
        FieldCreate(
            name=f"it-{uuid4().hex[:8]}",
            description="integration test",
            boundary=BOUNDARY,
            province="Córdoba",
            country="AR",
        )
    )
    try:
        assert field.area_hectares > 0
        fetched = store.get(field.id).value
        assert fetched.boundary.type == "Polygon"
        assert fetched.name == field.name

        published = store.publish(field.id)
        assert published.visibility == "public" and published.public_slug
        public = store.get_public(published.public_slug or "")
        assert public.value.id == field.id
        assert public.published_at is not None

        unpublished = store.unpublish(field.id)
        assert unpublished.visibility == "private"
    finally:
        store.archive(field.id)
    with pytest.raises(FieldNotFound):
        store.get(field.id)


def test_timelapse_repository_against_supabase() -> None:
    store = PostgresFieldStore()
    repo = PostgresTimelapseRepository()
    field = store.create(
        FieldCreate(name=f"it-tl-{uuid4().hex[:8]}", boundary=BOUNDARY, country="AR")
    )
    try:
        geom_id = repo.get_or_create_geometry_version(
            field_id=field.id, boundary=field.boundary, area_hectares=field.area_hectares
        )
        assert geom_id == repo.get_or_create_geometry_version(
            field_id=field.id, boundary=field.boundary, area_hectares=field.area_hectares
        )

        req_hash = repo.compute_request_hash(
            field_id=field.id,
            geometry_version_id=geom_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            layers=["rgb", "ndvi"],
            is_demo=True,
        )
        job = repo.create_job(
            field_id=field.id,
            geometry_version_id=geom_id,
            request_hash=req_hash,
            parameters={"start_date": "2024-01-01", "end_date": "2024-01-10"},
        )
        claimed = repo.claim_next_job(lease_seconds=60)
        assert claimed is not None
        claimed_job, token = claimed
        assert claimed_job.id == job.id
        repo.update_job_status(
            job_id=job.id, status="failed", progress=0.0,
            lease_token=token, error_code="TEST", error_message="integration test",
        )
        done = repo.get_job(job.id)
        assert done is not None and done.status == "failed"
        assert repo.get_job_parameters(job.id)["start_date"] == "2024-01-01"
    finally:
        store.archive(field.id)
