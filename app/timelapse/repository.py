from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.config import settings
from app.db import get_engine
from app.models import (
    assets as assets_table,
    datasets as datasets_table,
    fields as fields_table,
    frames as frames_table,
    geometry_versions as geometry_versions_table,
    jobs as jobs_table,
    multipolygon_geography,
    publications as publications_table,
)
from app.schemas import PolygonGeometry
from app.timelapse.schemas import (
    TimelapseDatasetSummary,
    TimelapseJobResponse,
    TimelapseManifest,
)


class TimelapseRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = str(settings.db_file_path)
        else:
            self.db_path = str(db_path)
        self.init_db()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS field_geometry_versions (
                id TEXT PRIMARY KEY,
                field_id TEXT NOT NULL,
                boundary TEXT NOT NULL,
                geometry_hash TEXT NOT NULL,
                area_hectares REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timelapse_jobs (
                id TEXT PRIMARY KEY,
                field_id TEXT NOT NULL,
                geometry_version_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0.0,
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_token TEXT,
                lease_until TEXT,
                dataset_id TEXT,
                error_code TEXT,
                error_message TEXT,
                parameters TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_request_hash ON timelapse_jobs(request_hash);
            CREATE INDEX IF NOT EXISTS idx_jobs_status_lease ON timelapse_jobs(status, lease_until);

            CREATE TABLE IF NOT EXISTS timelapse_datasets (
                id TEXT PRIMARY KEY,
                field_id TEXT NOT NULL,
                geometry_version_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                timezone TEXT NOT NULL,
                processing_version TEXT NOT NULL,
                status TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 0,
                generated_at TEXT NOT NULL,
                manifest_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_datasets_field ON timelapse_datasets(field_id);
            CREATE INDEX IF NOT EXISTS idx_datasets_hash ON timelapse_datasets(request_hash);

            CREATE TABLE IF NOT EXISTS field_public_timelapse (
                field_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                published_at TEXT NOT NULL
            );
            """)

    def get_or_create_geometry_version(
        self,
        field_id: UUID,
        boundary: PolygonGeometry,
        area_hectares: float,
    ) -> UUID:
        raw_coords = json.dumps(boundary.coordinates, sort_keys=True)
        geom_hash = hashlib.sha256(raw_coords.encode()).hexdigest()

        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM field_geometry_versions WHERE field_id = ? AND geometry_hash = ?",
                (str(field_id), geom_hash),
            ).fetchone()
            if row:
                return UUID(row["id"])

            version_id = uuid4()
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO field_geometry_versions (id, field_id, boundary, geometry_hash, area_hectares, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(version_id),
                    str(field_id),
                    boundary.model_dump_json(),
                    geom_hash,
                    area_hectares,
                    now_iso,
                ),
            )
            return version_id

    def get_latest_geometry_version(self, field_id: UUID) -> UUID | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM field_geometry_versions WHERE field_id = ? ORDER BY created_at DESC LIMIT 1",
                (str(field_id),),
            ).fetchone()
            return UUID(row["id"]) if row else None

    @staticmethod
    def compute_request_hash(
        field_id: UUID,
        geometry_version_id: UUID,
        start_date: date,
        end_date: date,
        layers: list[str],
        is_demo: bool,
    ) -> str:
        key = (
            f"{field_id}:{geometry_version_id}:{start_date.isoformat()}:{end_date.isoformat()}:"
            f"{','.join(sorted(layers))}:{is_demo}:{settings.timelapse_processing_version}"
        )
        return hashlib.sha256(key.encode()).hexdigest()

    def find_ready_dataset_for_hash(self, request_hash: str) -> TimelapseManifest | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM timelapse_datasets WHERE request_hash = ? AND status IN ('ready', 'partial') ORDER BY generated_at DESC LIMIT 1",
                (request_hash,),
            ).fetchone()
            if row:
                data = json.loads(row["manifest_json"])
                return TimelapseManifest.model_validate(data)
            return None

    def find_active_job(self, request_hash: str) -> TimelapseJobResponse | None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM timelapse_jobs
                WHERE request_hash = ? AND (
                    status = 'queued' OR
                    (status = 'processing' AND (lease_until IS NULL OR lease_until > ?))
                )
                ORDER BY created_at DESC LIMIT 1
                """,
                (request_hash, now_iso),
            ).fetchone()
            if row:
                return self._row_to_job(row)
            return None

    def create_job(
        self,
        field_id: UUID,
        geometry_version_id: UUID,
        request_hash: str,
        parameters: dict[str, Any],
    ) -> TimelapseJobResponse:
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO timelapse_jobs (
                    id, field_id, geometry_version_id, request_hash, status, progress, attempts,
                    parameters, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', 0.0, 0, ?, ?, ?)
                """,
                (
                    str(job_id),
                    str(field_id),
                    str(geometry_version_id),
                    request_hash,
                    json.dumps(parameters),
                    now_iso,
                    now_iso,
                ),
            )

        return TimelapseJobResponse(
            id=job_id,
            field_id=field_id,
            geometry_version_id=geometry_version_id,
            request_hash=request_hash,
            status="queued",
            progress=0.0,
            dataset_id=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def get_job(self, job_id: UUID) -> TimelapseJobResponse | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM timelapse_jobs WHERE id = ?", (str(job_id),)).fetchone()
            if row:
                return self._row_to_job(row)
            return None

    def get_job_parameters(self, job_id: UUID) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT parameters FROM timelapse_jobs WHERE id = ?", (str(job_id),)
            ).fetchone()
            return json.loads(row["parameters"]) if row else None

    def claim_next_job(self, lease_seconds: int = 60) -> tuple[TimelapseJobResponse, str] | None:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        lease_token = uuid4().hex
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()

        with self._connection() as conn:
            # Find candidate queued or expired processing job
            row = conn.execute(
                """
                SELECT id FROM timelapse_jobs
                WHERE status = 'queued' OR (status = 'processing' AND lease_until < ?)
                ORDER BY created_at ASC LIMIT 1
                """,
                (now_iso,),
            ).fetchone()

            if not row:
                return None

            job_id_str = row["id"]
            cursor = conn.execute(
                """
                UPDATE timelapse_jobs
                SET status = 'processing', lease_token = ?, lease_until = ?,
                    attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND (status = 'queued' OR (status = 'processing' AND lease_until < ?))
                """,
                (lease_token, lease_until, now_iso, job_id_str, now_iso),
            )
            if cursor.rowcount == 0:
                return None

            claimed_row = conn.execute(
                "SELECT * FROM timelapse_jobs WHERE id = ?", (job_id_str,)
            ).fetchone()
            return self._row_to_job(claimed_row), lease_token

    def update_job_status(
        self,
        job_id: UUID,
        status: str,
        progress: float,
        lease_token: str | None = None,
        dataset_id: UUID | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            query = """
                UPDATE timelapse_jobs
                SET status = ?, progress = ?, dataset_id = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            """
            params: list[Any] = [
                status,
                progress,
                str(dataset_id) if dataset_id else None,
                error_code,
                error_message,
                now_iso,
                str(job_id),
            ]
            if lease_token:
                query += " AND lease_token = ?"
                params.append(lease_token)
            conn.execute(query, params)

    def save_dataset(self, manifest: TimelapseManifest, request_hash: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO timelapse_datasets (
                    id, field_id, geometry_version_id, request_hash, start_date, end_date,
                    timezone, processing_version, status, is_demo, generated_at, manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(manifest.dataset_id),
                    str(manifest.field_id),
                    str(manifest.geometry_version_id),
                    request_hash,
                    manifest.start_date.isoformat(),
                    manifest.end_date.isoformat(),
                    manifest.timezone,
                    manifest.processing_version,
                    manifest.status,
                    1 if manifest.is_demo else 0,
                    manifest.generated_at.isoformat(),
                    manifest.model_dump_json(),
                ),
            )

    def get_dataset(self, dataset_id: UUID) -> TimelapseManifest | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM timelapse_datasets WHERE id = ?", (str(dataset_id),)
            ).fetchone()
            if row:
                return TimelapseManifest.model_validate_json(row["manifest_json"])
            return None

    def list_datasets_for_field(self, field_id: UUID) -> list[TimelapseDatasetSummary]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, field_id, start_date, end_date, status, is_demo, generated_at, manifest_json
                FROM timelapse_datasets
                WHERE field_id = ?
                ORDER BY generated_at DESC
                """,
                (str(field_id),),
            ).fetchall()

            summaries: list[TimelapseDatasetSummary] = []
            for r in rows:
                manifest_dict = json.loads(r["manifest_json"])
                summaries.append(
                    TimelapseDatasetSummary(
                        id=UUID(r["id"]),
                        field_id=UUID(r["field_id"]),
                        start_date=date.fromisoformat(r["start_date"]),
                        end_date=date.fromisoformat(r["end_date"]),
                        status=r["status"],
                        is_demo=bool(r["is_demo"]),
                        generated_at=datetime.fromisoformat(r["generated_at"]),
                        frames_count=len(manifest_dict.get("frames", [])),
                    )
                )
            return summaries

    def publish_dataset(self, field_id: UUID, dataset_id: UUID) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO field_public_timelapse (field_id, dataset_id, published_at)
                VALUES (?, ?, ?)
                """,
                (str(field_id), str(dataset_id), now_iso),
            )

    def get_published_dataset_for_field(self, field_id: UUID) -> TimelapseManifest | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT d.manifest_json FROM field_public_timelapse p
                JOIN timelapse_datasets d ON p.dataset_id = d.id
                WHERE p.field_id = ?
                """,
                (str(field_id),),
            ).fetchone()
            if row:
                return TimelapseManifest.model_validate_json(row["manifest_json"])
            return None

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> TimelapseJobResponse:
        return TimelapseJobResponse(
            id=UUID(row["id"]),
            field_id=UUID(row["field_id"]),
            geometry_version_id=UUID(row["geometry_version_id"]),
            request_hash=row["request_hash"],
            status=row["status"],
            progress=float(row["progress"]),
            dataset_id=UUID(row["dataset_id"]) if row["dataset_id"] else None,
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# ── Supabase Postgres ─────────────────────────────────────────────────────────

# Los estados externos del contrato HTTP no cambian; sólo varía el almacenamiento.
_DATASET_STATUS_TO_DB = {"ready": "completed", "partial": "partial", "failed": "failed"}
_JOB_API_TO_STATE = {
    "queued": "queued",
    "processing": "running",
    "ready": "done",
    "partial": "done",
    "failed": "failed",
}
_JOB_STATE_TO_API = {
    "queued": "queued",
    "running": "processing",
    "done": "ready",
    "failed": "failed",
}


class PostgresTimelapseRepository:
    """Timelapse sobre Supabase: `timelapse.*` para datasets/geometrías y
    `ops.jobs` (kind='timelapse') para la cola con leases, según la decisión de
    base de datos única. El contrato HTTP queda intacto.
    """

    compute_request_hash = staticmethod(TimelapseRepository.compute_request_hash)

    # ── geometrías ─────────────────────────────────────────────────────────

    def get_or_create_geometry_version(
        self,
        field_id: UUID,
        boundary: PolygonGeometry,
        area_hectares: float,
    ) -> UUID:
        raw_coords = json.dumps(boundary.coordinates, sort_keys=True)
        geom_hash = hashlib.sha256(raw_coords.encode()).hexdigest()

        find = sa.select(geometry_versions_table.c.id).where(
            geometry_versions_table.c.field_id == field_id,
            geometry_versions_table.c.geometry_hash == geom_hash,
        )
        with get_engine().begin() as conn:
            existing = conn.execute(find).scalar_one_or_none()
            if existing is not None:
                return existing

            stmt = (
                postgresql.insert(geometry_versions_table)
                .values(
                    field_id=field_id,
                    boundary=multipolygon_geography(boundary.model_dump_json()),
                    geometry_hash=geom_hash,
                    area_hectares=area_hectares,
                )
                .on_conflict_do_nothing(index_elements=["field_id", "geometry_hash"])
                .returning(geometry_versions_table.c.id)
            )
            version_id = conn.execute(stmt).scalar_one_or_none()
            if version_id is None:  # carrera entre workers
                version_id = conn.execute(find).scalar_one()
            return version_id

    def get_latest_geometry_version(self, field_id: UUID) -> UUID | None:
        with get_engine().connect() as conn:
            return conn.execute(
                sa.select(geometry_versions_table.c.id)
                .where(geometry_versions_table.c.field_id == field_id)
                .order_by(geometry_versions_table.c.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()

    # ── datasets ───────────────────────────────────────────────────────────

    def find_ready_dataset_for_hash(self, request_hash: str) -> TimelapseManifest | None:
        with get_engine().connect() as conn:
            manifest = conn.execute(
                sa.select(datasets_table.c.manifest)
                .where(
                    datasets_table.c.request_hash == request_hash,
                    datasets_table.c.status.in_(["completed", "partial"]),
                )
                .order_by(datasets_table.c.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return TimelapseManifest.model_validate(manifest) if manifest else None

    def save_dataset(self, manifest: TimelapseManifest, request_hash: str) -> None:
        manifest_json = manifest.model_dump(mode="json")
        db_status = _DATASET_STATUS_TO_DB[manifest.status]
        weather_by_date = {w.date: w for w in manifest.weather_daily}

        with get_engine().begin() as conn:
            conn.execute(
                postgresql.insert(datasets_table)
                .values(
                    id=manifest.dataset_id,
                    field_id=manifest.field_id,
                    source_mode="synthetic" if manifest.is_demo else "real",
                    is_demo=manifest.is_demo,
                    date_from=manifest.start_date,
                    date_to=manifest.end_date,
                    status=db_status,
                    request_hash=request_hash,
                    manifest=manifest_json,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "status": db_status,
                        "request_hash": request_hash,
                        "manifest": manifest_json,
                        "is_demo": manifest.is_demo,
                        "date_from": manifest.start_date,
                        "date_to": manifest.end_date,
                    },
                )
            )

            # Tablas normalizadas (consultas futuras / certificación).
            conn.execute(
                frames_table.delete().where(
                    frames_table.c.dataset_id == manifest.dataset_id
                )
            )
            for frame in manifest.frames:
                weather = weather_by_date.get(frame.local_date)
                frame_id = conn.execute(
                    frames_table.insert()
                    .values(
                        dataset_id=manifest.dataset_id,
                        frame_date=frame.local_date,
                        weather=weather.model_dump(mode="json") if weather else None,
                        satellite=frame.model_dump(mode="json", exclude={"assets"}),
                    )
                    .returning(frames_table.c.id)
                ).scalar_one()
                for asset in frame.assets:
                    conn.execute(
                        assets_table.insert().values(
                            frame_id=frame_id,
                            layer=asset.layer,
                            storage_ref=asset.url,
                            mime="image/png",
                        )
                    )

    def get_dataset(self, dataset_id: UUID) -> TimelapseManifest | None:
        with get_engine().connect() as conn:
            manifest = conn.execute(
                sa.select(datasets_table.c.manifest).where(
                    datasets_table.c.id == dataset_id
                )
            ).scalar_one_or_none()
            return TimelapseManifest.model_validate(manifest) if manifest else None

    def list_datasets_for_field(self, field_id: UUID) -> list[TimelapseDatasetSummary]:
        with get_engine().connect() as conn:
            rows = conn.execute(
                sa.select(
                    datasets_table.c.id,
                    datasets_table.c.field_id,
                    datasets_table.c.date_from,
                    datasets_table.c.date_to,
                    datasets_table.c.status,
                    datasets_table.c.is_demo,
                    datasets_table.c.created_at,
                    datasets_table.c.manifest,
                )
                .where(datasets_table.c.field_id == field_id)
                .order_by(datasets_table.c.created_at.desc())
            ).mappings().all()

        summaries: list[TimelapseDatasetSummary] = []
        for r in rows:
            manifest = r["manifest"] or {}
            summaries.append(
                TimelapseDatasetSummary(
                    id=r["id"],
                    field_id=r["field_id"],
                    start_date=r["date_from"],
                    end_date=r["date_to"],
                    status=manifest.get("status") or r["status"],
                    is_demo=bool(r["is_demo"]),
                    generated_at=datetime.fromisoformat(
                        manifest.get("generated_at", r["created_at"].isoformat())
                    ),
                    frames_count=len(manifest.get("frames", [])),
                )
            )
        return summaries

    def publish_dataset(self, field_id: UUID, dataset_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        with get_engine().begin() as conn:
            slug = conn.execute(
                sa.select(fields_table.c.public_slug).where(
                    fields_table.c.id == field_id
                )
            ).scalar_one_or_none() or uuid4().hex[:12]

            # Una sola publicación activa por field: se cierran las anteriores.
            other_datasets = sa.select(datasets_table.c.id).where(
                datasets_table.c.field_id == field_id,
                datasets_table.c.id != dataset_id,
            )
            conn.execute(
                publications_table.update()
                .where(
                    publications_table.c.dataset_id.in_(other_datasets),
                    publications_table.c.unpublished_at.is_(None),
                )
                .values(unpublished_at=now)
            )

            conn.execute(
                datasets_table.update()
                .where(datasets_table.c.id == dataset_id)
                .values(is_public=True, public_slug=slug)
            )
            conn.execute(
                postgresql.insert(publications_table)
                .values(dataset_id=dataset_id, public_slug=slug, published_at=now)
                .on_conflict_do_update(
                    index_elements=["public_slug"],
                    set_={
                        "dataset_id": dataset_id,
                        "published_at": now,
                        "unpublished_at": None,
                    },
                )
            )

    def get_published_dataset_for_field(self, field_id: UUID) -> TimelapseManifest | None:
        with get_engine().connect() as conn:
            manifest = conn.execute(
                sa.select(datasets_table.c.manifest)
                .select_from(
                    publications_table.join(
                        datasets_table,
                        publications_table.c.dataset_id == datasets_table.c.id,
                    )
                )
                .where(
                    datasets_table.c.field_id == field_id,
                    publications_table.c.unpublished_at.is_(None),
                )
                .order_by(publications_table.c.published_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return TimelapseManifest.model_validate(manifest) if manifest else None

    # ── cola de jobs (ops.jobs) ─────────────────────────────────────────────

    def find_active_job(self, request_hash: str) -> TimelapseJobResponse | None:
        now = datetime.now(timezone.utc)
        with get_engine().connect() as conn:
            row = conn.execute(
                sa.select(jobs_table)
                .where(
                    jobs_table.c.kind == "timelapse",
                    jobs_table.c.payload["request_hash"].astext == request_hash,
                    sa.or_(
                        jobs_table.c.state == "queued",
                        sa.and_(
                            jobs_table.c.state == "running",
                            sa.or_(
                                jobs_table.c.lease_until.is_(None),
                                jobs_table.c.lease_until > now,
                            ),
                        ),
                    ),
                )
                .order_by(jobs_table.c.created_at.desc())
                .limit(1)
            ).mappings().first()
            return self._row_to_job(row) if row else None

    def create_job(
        self,
        field_id: UUID,
        geometry_version_id: UUID,
        request_hash: str,
        parameters: dict[str, Any],
    ) -> TimelapseJobResponse:
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = {
            "request_hash": request_hash,
            "geometry_version_id": str(geometry_version_id),
            "parameters": parameters,
            "api_status": "queued",
        }
        with get_engine().begin() as conn:
            conn.execute(
                jobs_table.insert().values(
                    id=job_id,
                    kind="timelapse",
                    ref_id=field_id,
                    state="queued",
                    progress=0,
                    payload=payload,
                )
            )
        return TimelapseJobResponse(
            id=job_id,
            field_id=field_id,
            geometry_version_id=geometry_version_id,
            request_hash=request_hash,
            status="queued",
            progress=0.0,
            dataset_id=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def get_job(self, job_id: UUID) -> TimelapseJobResponse | None:
        with get_engine().connect() as conn:
            row = conn.execute(
                sa.select(jobs_table).where(
                    jobs_table.c.id == job_id, jobs_table.c.kind == "timelapse"
                )
            ).mappings().first()
            return self._row_to_job(row) if row else None

    def get_job_parameters(self, job_id: UUID) -> dict[str, Any] | None:
        with get_engine().connect() as conn:
            payload = conn.execute(
                sa.select(jobs_table.c.payload).where(
                    jobs_table.c.id == job_id, jobs_table.c.kind == "timelapse"
                )
            ).scalar_one_or_none()
            return (payload or {}).get("parameters")

    def claim_next_job(self, lease_seconds: int = 60) -> tuple[TimelapseJobResponse, str] | None:
        now = datetime.now(timezone.utc)
        lease_token = uuid4().hex
        lease_until = now + timedelta(seconds=lease_seconds)
        claim_sql = sa.text("""
            UPDATE ops.jobs
            SET state = 'running', lease_token = :token, lease_until = :until,
                attempts = attempts + 1, updated_at = now()
            WHERE id = (
                SELECT id FROM ops.jobs
                WHERE kind = 'timelapse'
                  AND (state = 'queued' OR (state = 'running' AND lease_until < :now))
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """)
        with get_engine().begin() as conn:
            row = conn.execute(
                claim_sql, {"token": lease_token, "until": lease_until, "now": now}
            ).mappings().first()
            if row is None:
                return None
            return self._row_to_job(row), lease_token

    def update_job_status(
        self,
        job_id: UUID,
        status: str,
        progress: float,
        lease_token: str | None = None,
        dataset_id: UUID | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with get_engine().begin() as conn:
            payload = conn.execute(
                sa.select(jobs_table.c.payload).where(jobs_table.c.id == job_id)
            ).scalar_one_or_none()
            if payload is None:
                return
            payload = dict(payload)
            payload["api_status"] = status
            if dataset_id is not None:
                payload["dataset_id"] = str(dataset_id)
            if error_code is not None:
                payload["error_code"] = error_code

            stmt = (
                jobs_table.update()
                .where(jobs_table.c.id == job_id)
                .values(
                    state=_JOB_API_TO_STATE[status],
                    progress=progress,
                    payload=payload,
                    last_error=error_message,
                    updated_at=sa.func.now(),
                )
            )
            if lease_token:
                stmt = stmt.where(jobs_table.c.lease_token == lease_token)
            conn.execute(stmt)

    # ── mapping ────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_job(row: Any) -> TimelapseJobResponse:
        payload = row["payload"] or {}
        return TimelapseJobResponse(
            id=row["id"],
            field_id=row["ref_id"],
            geometry_version_id=UUID(payload["geometry_version_id"]),
            request_hash=payload["request_hash"],
            status=payload.get("api_status")
            or _JOB_STATE_TO_API.get(row["state"], "failed"),
            progress=float(row["progress"] or 0),
            dataset_id=UUID(payload["dataset_id"]) if payload.get("dataset_id") else None,
            error_code=payload.get("error_code"),
            error_message=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def get_timelapse_repository() -> TimelapseRepository | PostgresTimelapseRepository:
    """`DATABASE_URL` presente → Supabase; si no, SQLite local (dev/tests)."""
    if settings.use_supabase:
        return PostgresTimelapseRepository()
    return TimelapseRepository()


timelapse_repository = get_timelapse_repository()
