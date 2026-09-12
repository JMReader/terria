"""Pre-genera y cachea en Supabase Storage la portada NDVI de cada certificación.

Uso:
    uv run python scripts/seed_cert_heroes.py                    # todas
    uv run python scripts/seed_cert_heroes.py --min-version 10   # sólo las nuevas
    uv run python scripts/seed_cert_heroes.py --name Marcos

Fuerza el upload a Storage incluso cuando el PNG ya existe en disco local, para
que el endpoint público `/hero.png` no dependa del filesystem de la máquina que
emitió el certificado. La generación usa Sentinel-2 vía Microsoft Planetary
Computer, así que no requiere cuenta Copernicus.
"""

from __future__ import annotations

import argparse
import logging

from app.blockchain.repository import get_certification_repository
from app.blockchain.service import get_certification_hero_image
from app.blockchain.storage import SupabasePayloadStorage
from app.config import settings
from app.store import get_field_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("seed_cert_heroes")


def _asset_storage() -> SupabasePayloadStorage | None:
    if not (settings.supabase_url and settings.supabase_service_role_key):
        return None
    try:
        return SupabasePayloadStorage(bucket=settings.assets_storage_bucket)
    except RuntimeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Portadas NDVI de certificaciones TERRIA.")
    parser.add_argument("--name", default=None, help="Filtro por nombre de campo (substring)")
    parser.add_argument(
        "--min-version",
        type=int,
        default=1,
        help="Sólo certificaciones con version >= N (ej. 10 para las mensuales nuevas)",
    )
    args = parser.parse_args()

    store = get_field_store()
    repository = get_certification_repository()
    storage = _asset_storage()

    fields = store.list()
    if args.name:
        fields = [field for field in fields if args.name.lower() in field.name.lower()]
    if not fields:
        raise SystemExit("No hay campos que coincidan con el filtro.")

    uploaded = 0
    for field in fields:
        for certification in repository.list_for_field(field.id):
            if certification.version < args.min_version:
                continue
            image = get_certification_hero_image(certification.cert_uid)
            size = len(image) if image else 0
            status = f"{size} B" if image else "sin imagen"
            if image is not None and storage is not None:
                try:
                    storage.upload(
                        f"certificates/{certification.cert_uid}.png", image, "image/png"
                    )
                    status += " → Storage"
                    uploaded += 1
                except Exception as exc:  # noqa: BLE001 - caching is best-effort
                    status += f" (Storage falló: {exc})"
            logger.info(
                "%-42s V%d cert %s -> %s",
                field.name,
                certification.version,
                certification.cert_uid,
                status,
            )

    print(f"\nPortadas listas ({uploaded} subidas a Supabase Storage).\n")


if __name__ == "__main__":
    main()
