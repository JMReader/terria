"""Esquema inicial de dominio TERRIA.

Ejecuta el SQL canónico de `supabase/migrations/` — la misma fuente que aplica
`supabase db push` — para que una base vacía quede igual que la creada por el
flujo Supabase CLI. En bases donde ese archivo ya se aplicó, marcar la revisión
con `alembic stamp 0001` en lugar de correr `upgrade`.

Revision ID: 0001
Revises:
Create Date: 2026-09-12
"""
from __future__ import annotations

from pathlib import Path

import psycopg
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None

_SQL_FILE = "20260912064046_terria_initial_schema.sql"


def _script_path() -> Path:
    return (
        Path(__file__).resolve().parents[2] / "supabase" / "migrations" / _SQL_FILE
    )


def upgrade() -> None:
    # El script usa bloques $$ (plpgsql): se ejecuta entero con un cursor de
    # protocolo simple (ClientCursor), que admite multi-statements.
    conn = op.get_bind().connection.driver_connection
    psycopg.ClientCursor(conn).execute(_script_path().read_text(encoding="utf-8"))


def downgrade() -> None:
    for schema in ("cert", "ops", "timelapse", "agro", "climate", "satellite", "core"):
        op.execute(f"drop schema if exists {schema} cascade")
