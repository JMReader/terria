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
    # Base pública del frontend — se imprime en el PDF del certificado
    terria_public_web_base: str = "http://localhost:3000"

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
    terria_db_echo: bool = False

    # Owner de las filas creadas por el backend mientras no haya Auth por request.
    # Si falta y Supabase está activo, se provisiona `terria_system_email` vía Admin API.
    terria_default_owner_id: str | None = None
    terria_system_email: str = "terria-system@terria.local"

    # Conexión para Alembic (default: DATABASE_DIRECT_URL; cae a DATABASE_URL si no resuelve).
    migration_database_url: str | None = None

    timelapse_storage_dir: str = "data/storage"
    # 0.3.0: paginado del catálogo CDSE (campaña completa) + serie mensual.
    timelapse_processing_version: str = "0.3.0"
    timelapse_max_image_age_days: int = 10

    # ── Copernicus CDSE (Sentinel imagery) ────────────────────────────────────
    cdse_client_id: str | None = None
    cdse_client_secret: str | None = None
    cdse_token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    cdse_catalogue_url: str = "https://stac.dataspace.copernicus.eu/v1/search"
    cdse_process_url: str = "https://sh.dataspace.copernicus.eu/process/v1"
    cdse_statistics_url: str = "https://sh.dataspace.copernicus.eu/statistics/v1"
    # Tope total de escenas por dataset (se pagina el catálogo) y tamaño de página.
    cdse_max_scenes: int = 200
    cdse_page_size: int = 100

    # ── Weather provider ──────────────────────────────────────────────────────
    weather_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"

    # ── Certificación en Solana ───────────────────────────────────────────────
    # "local" usa un validador en memoria (sin red ni SOL); "devnet" usa un RPC real.
    solana_anchor_provider: str = "local"
    solana_cluster: str = "devnet"
    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_memo_program_id: str = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
    # JSON byte array, base58 o base64. Nunca commitear; sólo variable de entorno.
    solana_issuer_secret_key: str | None = None
    cert_schema_version: str = "terria.cert/4"
    cert_algorithm_version: str = "jcs+sha256/1"
    cert_storage_bucket: str = "cert-payloads"
    # Imagen NDVI de portada del certificado (Supabase Storage).
    assets_storage_bucket: str = "terria-assets"
    cert_hero_generate: bool = True

    @property
    def use_devnet_anchor(self) -> bool:
        return self.solana_anchor_provider == "devnet"

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
