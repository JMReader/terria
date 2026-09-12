"""Alineación del backend Python con el schema de dominio.

- `core.fields.published_at`: timestamp de primera publicación.
- `ops.jobs`: `payload` (params/request_hash/resultado), `progress`, `lease_token`.
- `timelapse.geometry_versions`: historial de geometrías por field.

El SQL canónico vive en `supabase/migrations/`; este revision sólo lo ejecuta.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-12
"""
from __future__ import annotations

from pathlib import Path

import psycopg
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels = None
depends_on = None

_SQL_FILE = "20260912070000_timelapse_backend_alignment.sql"


def upgrade() -> None:
    path = (
        Path(__file__).resolve().parents[2] / "supabase" / "migrations" / _SQL_FILE
    )
    conn = op.get_bind().connection.driver_connection
    psycopg.ClientCursor(conn).execute(path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("drop policy if exists \"owners read geometry versions\" on timelapse.geometry_versions")
    op.execute("drop table if exists timelapse.geometry_versions")
    op.execute("drop index if exists ops.jobs_timelapse_request_hash_ix")
    op.execute(
        "alter table ops.jobs "
        "drop column if exists lease_token, "
        "drop column if exists progress, "
        "drop column if exists payload"
    )
    op.execute("alter table core.fields drop column if exists published_at")
