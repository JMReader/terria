from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import normalize_url
from app.models import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

target_metadata = metadata


def _candidate_urls() -> list[str]:
    """Orden de preferencia: conexión directa/sesión para migraciones; el pooler
    transaccional queda como fallback cuando el host directo no resuelve."""
    raw = [
        settings.migration_database_url,
        settings.database_direct_url,
        settings.database_url,
    ]
    return [normalize_url(u) for u in raw if u]


def _connect(urls: list[str]) -> Engine:
    if not urls:
        raise RuntimeError(
            "Sin conexión para migraciones: configurá MIGRATION_DATABASE_URL, "
            "DATABASE_DIRECT_URL o DATABASE_URL"
        )
    last_exc: Exception | None = None
    for url in urls:
        engine = create_engine(
            url, poolclass=NullPool, connect_args={"prepare_threshold": None}
        )
        try:
            probe = engine.connect()
            probe.close()
            return engine
        except Exception as exc:  # noqa: BLE001 - probamos el siguiente candidato
            logger.warning(
                "No se pudo conectar para migraciones (%s): %s",
                engine.url.render_as_string(hide_password=True),
                type(exc).__name__,
            )
            engine.dispose()
            last_exc = exc
    raise RuntimeError("Ninguna URL de migración conectó") from last_exc


def run_migrations_online() -> None:
    connectable = _connect(_candidate_urls())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


def run_migrations_offline() -> None:
    urls = _candidate_urls()
    if not urls:
        raise RuntimeError("Sin URL de base de datos configurada")
    context.configure(
        url=urls[0],
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="public",
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
