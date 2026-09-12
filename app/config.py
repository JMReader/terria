from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    terria_env: str = "development"
    terria_cors_origins: str = "http://localhost:3000"

    # ── Supabase ──────────────────────────────────────────────────────────────
    # Pooler transaccional (:6543) — API y worker serverless
    database_url: str | None = None
    # Conexión directa (:5432) — solo Alembic / migraciones
    database_direct_url: str | None = None

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None

    # ── SQLite fallback (dev local sin Supabase) ──────────────────────────────
    terria_db_path: str = "data/terria.db"
    timelapse_storage_dir: str = "data/storage"
    timelapse_processing_version: str = "0.2.0"
    timelapse_max_image_age_days: int = 10

    # ── Copernicus CDSE (Sentinel imagery) ────────────────────────────────────
    cdse_client_id: str | None = None
    cdse_client_secret: str | None = None
    cdse_token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    cdse_catalogue_url: str = "https://stac.dataspace.copernicus.eu/v1/search"
    cdse_process_url: str = "https://sh.dataspace.copernicus.eu/process/v1"
    cdse_statistics_url: str = "https://sh.dataspace.copernicus.eu/statistics/v1"
    cdse_max_scenes: int = 12

    # ── Weather provider ──────────────────────────────────────────────────────
    weather_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"

    @property
    def use_supabase(self) -> bool:
        """True cuando DATABASE_URL está configurada (modo Supabase activo)."""
        return bool(self.database_url)

    @property
    def db_file_path(self) -> Path:
        """Solo se usa en modo SQLite local."""
        path = Path(self.terria_db_path)
        if path.name != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def assets_dir(self) -> Path:
        path = Path(self.timelapse_storage_dir) / "assets"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
