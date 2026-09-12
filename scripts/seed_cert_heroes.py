"""Pre-genera y cachea en Supabase Storage la portada NDVI de cada certificación.

Uso:
    uv run python scripts/seed_cert_heroes.py

No toca Supabase Storage si el backend es SQLite: en ese caso solo calienta el
archivo local. La generación usa Sentinel-2 vía Microsoft Planetary Computer, así
que no requiere cuenta Copernicus.
"""

from __future__ import annotations

import logging

from app.blockchain.repository import get_certification_repository
from app.blockchain.service import get_certification_hero_image
from app.store import get_field_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("seed_cert_heroes")


def main() -> None:
    store = get_field_store()
    repository = get_certification_repository()

    for field in store.list():
        for certification in repository.list_for_field(field.id):
            image = get_certification_hero_image(certification.cert_uid)
            size = len(image) if image else 0
            logger.info(
                "%-42s cert %s -> %s",
                field.name,
                certification.cert_uid,
                f"{size} B" if image else "sin imagen",
            )

    print("\nPortadas listas (disco local y/o Supabase Storage).\n")


if __name__ == "__main__":
    main()
