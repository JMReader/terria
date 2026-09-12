from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def normalize_url(url: str) -> str:
    """Ensure the SQLAlchemy URL uses the psycopg (v3) driver."""
    parsed = make_url(url)
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def get_engine() -> Engine:
    """Engine compartido para Supabase Postgres.

    `NullPool` + `prepare_threshold=None`: requerido por el pooler transaccional
    de Supabase (:6543), que no soporta prepared statements ni estado de sesión.
    """
    global _engine
    if _engine is None:
        if not settings.use_supabase:
            raise RuntimeError("DATABASE_URL no configurada (modo Supabase inactivo)")
        _engine = create_engine(
            normalize_url(settings.database_url or ""),
            poolclass=NullPool,
            connect_args={"prepare_threshold": None},
            echo=settings.terria_db_echo,
        )
    return _engine


def db_ping() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health check no debe propagar
        logger.warning("Database ping failed: %s", type(exc).__name__)
        return False


def reset_engine() -> None:
    """Descarta el engine cacheado (tests / cambio de settings en runtime)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
