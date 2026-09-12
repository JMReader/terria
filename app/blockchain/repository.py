from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from app.config import settings


@dataclass
class CertificationRecord:
    id: UUID
    field_id: UUID
    version: int
    cert_uid: str
    schema_version: str
    algorithm_version: str
    period_from: int
    period_to: int
    status: str
    content_hash: str | None
    prev_content_hash: str | None
    issued_at: datetime | None
    created_at: datetime


@dataclass
class AnchorRecord:
    certification_id: UUID
    provider: str
    cluster: str
    memo_payload: str
    tx_signature: str | None
    slot: int | None
    block_time: datetime | None
    status: str
    attempts: int
    error: str | None


class CertificationRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(settings.db_file_path if db_path is None else db_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS certifications (
                id TEXT PRIMARY KEY,
                field_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                cert_uid TEXT NOT NULL UNIQUE,
                schema_version TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                period_from INTEGER NOT NULL,
                period_to INTEGER NOT NULL,
                status TEXT NOT NULL,
                content_hash TEXT,
                prev_content_hash TEXT,
                issued_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (field_id, version)
            );
            CREATE INDEX IF NOT EXISTS idx_certifications_field ON certifications(field_id);

            CREATE TABLE IF NOT EXISTS cert_payloads (
                certification_id TEXT PRIMARY KEY,
                canonical_bytes BLOB NOT NULL,
                byte_size INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cert_anchors (
                certification_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                cluster TEXT NOT NULL,
                memo_payload TEXT NOT NULL,
                tx_signature TEXT,
                slot INTEGER,
                block_time TEXT,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL,
                confirmed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS anchor_jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL DEFAULT 'anchor',
                ref_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                not_before TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_anchor_jobs_state ON anchor_jobs(state);
            """)

    def next_version(self, field_id: UUID) -> int:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next FROM certifications WHERE field_id = ?",
                (str(field_id),),
            ).fetchone()
            return int(row["next"])

    def previous_content_hash(self, field_id: UUID) -> str | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT content_hash FROM certifications
                WHERE field_id = ? AND content_hash IS NOT NULL
                ORDER BY version DESC LIMIT 1
                """,
                (str(field_id),),
            ).fetchone()
            return row["content_hash"] if row else None

    def create_certification(
        self,
        *,
        field_id: UUID,
        version: int,
        cert_uid: str,
        schema_version: str,
        algorithm_version: str,
        period_from: int,
        period_to: int,
        status: str,
        content_hash: str,
        prev_content_hash: str | None,
        issued_at: datetime | None,
    ) -> CertificationRecord:
        certification_id = uuid4()
        now = datetime.now(timezone.utc)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO certifications (
                    id, field_id, version, cert_uid, schema_version, algorithm_version,
                    period_from, period_to, status, content_hash, prev_content_hash,
                    issued_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(certification_id),
                    str(field_id),
                    version,
                    cert_uid,
                    schema_version,
                    algorithm_version,
                    period_from,
                    period_to,
                    status,
                    content_hash,
                    prev_content_hash,
                    issued_at.isoformat() if issued_at else None,
                    now.isoformat(),
                ),
            )
            row = conn.execute(
                "SELECT * FROM certifications WHERE id = ?", (str(certification_id),)
            ).fetchone()
        return self._row_to_certification(row)

    def save_payload(self, certification_id: UUID, payload: bytes, content_hash: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cert_payloads (
                    certification_id, canonical_bytes, byte_size, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(certification_id), sqlite3.Binary(payload), len(payload), content_hash, now),
            )

    def get_payload(self, certification_id: UUID) -> bytes | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT canonical_bytes FROM cert_payloads WHERE certification_id = ?",
                (str(certification_id),),
            ).fetchone()
            return bytes(row["canonical_bytes"]) if row else None

    def set_status(
        self, certification_id: UUID, status: str, issued_at: datetime | None = None
    ) -> CertificationRecord:
        with self._get_connection() as conn:
            if issued_at is not None:
                conn.execute(
                    "UPDATE certifications SET status = ?, issued_at = ? WHERE id = ?",
                    (status, issued_at.isoformat(), str(certification_id)),
                )
            else:
                conn.execute(
                    "UPDATE certifications SET status = ? WHERE id = ?",
                    (status, str(certification_id)),
                )
            row = conn.execute(
                "SELECT * FROM certifications WHERE id = ?", (str(certification_id),)
            ).fetchone()
        return self._row_to_certification(row)

    def save_anchor(
        self,
        *,
        certification_id: UUID,
        provider: str,
        cluster: str,
        memo_payload: str,
        tx_signature: str | None,
        slot: int | None,
        block_time: datetime | None,
        status: str,
        attempts: int,
        error: str | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cert_anchors (
                    certification_id, provider, cluster, memo_payload, tx_signature, slot,
                    block_time, status, attempts, error, created_at, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(certification_id),
                    provider,
                    cluster,
                    memo_payload,
                    tx_signature,
                    slot,
                    block_time.isoformat() if block_time else None,
                    status,
                    attempts,
                    error,
                    now.isoformat(),
                    now.isoformat() if status == "confirmed" else None,
                ),
            )

    def get_anchor(self, certification_id: UUID) -> AnchorRecord | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM cert_anchors WHERE certification_id = ?", (str(certification_id),)
            ).fetchone()
            return self._row_to_anchor(row) if row else None

    def enqueue_anchor_job(self, certification_id: UUID, error: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO anchor_jobs (
                    id, kind, ref_id, state, attempts, last_error, created_at, updated_at
                ) VALUES (?, 'anchor', ?, 'queued', 0, ?, ?, ?)
                """,
                (uuid4().hex, str(certification_id), error, now, now),
            )

    def get(self, certification_id: UUID) -> CertificationRecord | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM certifications WHERE id = ?", (str(certification_id),)
            ).fetchone()
            return self._row_to_certification(row) if row else None

    def get_by_cert_uid(self, cert_uid: str) -> CertificationRecord | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM certifications WHERE cert_uid = ?", (cert_uid,)
            ).fetchone()
            return self._row_to_certification(row) if row else None

    def list_for_field(self, field_id: UUID) -> list[CertificationRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM certifications WHERE field_id = ? ORDER BY version DESC",
                (str(field_id),),
            ).fetchall()
            return [self._row_to_certification(row) for row in rows]

    @staticmethod
    def _row_to_certification(row: sqlite3.Row) -> CertificationRecord:
        return CertificationRecord(
            id=UUID(row["id"]),
            field_id=UUID(row["field_id"]),
            version=int(row["version"]),
            cert_uid=row["cert_uid"],
            schema_version=row["schema_version"],
            algorithm_version=row["algorithm_version"],
            period_from=int(row["period_from"]),
            period_to=int(row["period_to"]),
            status=row["status"],
            content_hash=row["content_hash"],
            prev_content_hash=row["prev_content_hash"],
            issued_at=datetime.fromisoformat(row["issued_at"]) if row["issued_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_anchor(row: sqlite3.Row) -> AnchorRecord:
        return AnchorRecord(
            certification_id=UUID(row["certification_id"]),
            provider=row["provider"],
            cluster=row["cluster"],
            memo_payload=row["memo_payload"],
            tx_signature=row["tx_signature"],
            slot=int(row["slot"]) if row["slot"] is not None else None,
            block_time=datetime.fromisoformat(row["block_time"]) if row["block_time"] else None,
            status=row["status"],
            attempts=int(row["attempts"]),
            error=row["error"],
        )


certification_repository = CertificationRepository()
