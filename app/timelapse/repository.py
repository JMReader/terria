from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import UUID, uuid4

from app.config import settings
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

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
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

        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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

        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM timelapse_jobs WHERE id = ?", (str(job_id),)).fetchone()
            if row:
                return self._row_to_job(row)
            return None

    def claim_next_job(self, lease_seconds: int = 60) -> tuple[TimelapseJobResponse, str] | None:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        lease_token = uuid4().hex
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()

        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM timelapse_datasets WHERE id = ?", (str(dataset_id),)
            ).fetchone()
            if row:
                return TimelapseManifest.model_validate_json(row["manifest_json"])
            return None

    def list_datasets_for_field(self, field_id: UUID) -> list[TimelapseDatasetSummary]:
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO field_public_timelapse (field_id, dataset_id, published_at)
                VALUES (?, ?, ?)
                """,
                (str(field_id), str(dataset_id), now_iso),
            )

    def get_published_dataset_for_field(self, field_id: UUID) -> TimelapseManifest | None:
        with self._get_connection() as conn:
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


timelapse_repository = TimelapseRepository()
