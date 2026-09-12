"""Emite y ancla los snapshots mensuales acumulados (certificación viva).

Por cada campo y cada mes con datos se emite una versión nueva cuyo snapshot
incluye TODO el historial hasta ese mes, encadenada con `prev_content_hash`.
Idempotente: cada mes usa un `cert_uid` determinístico, así que re-ejecutar no
duplica versiones ya emitidas.

Uso:
    uv run python scripts/seed_monthly_certifications.py            # los 3 campos reales
    uv run python scripts/seed_monthly_certifications.py --name Marcos
    uv run python scripts/seed_monthly_certifications.py --no-anchor  # sólo emite (sin blockchain)

Usa el dataset listo más reciente de cada campo (el de la campaña completa), no
todo el historial de datasets, para no duplicar observaciones.
"""

from __future__ import annotations

import argparse
import logging

from app.blockchain.service import issue_monthly_certifications
from app.store import get_field_store
from app.timelapse.repository import get_timelapse_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("seed_monthly_certifications")


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshots mensuales acumulados de TERRIA.")
    parser.add_argument("--name", default=None, help="Filtro por nombre de campo (substring)")
    parser.add_argument("--no-anchor", action="store_true", help="Emitir sin anclar en blockchain")
    args = parser.parse_args()

    store = get_field_store()
    repo = get_timelapse_repository()

    fields = store.list()
    if args.name:
        fields = [field for field in fields if args.name.lower() in field.name.lower()]
    if not fields:
        raise SystemExit("No hay campos que coincidan con el filtro.")

    total = 0
    for field in fields:
        logger.info("=== %s ===", field.name)
        datasets = [
            dataset
            for dataset in repo.list_datasets_for_field(field.id)
            if dataset.status == "ready" and not dataset.is_demo
        ][:1]
        if not datasets:
            logger.warning("Sin dataset listo; se omite.")
            continue

        certifications = issue_monthly_certifications(
            field=field, datasets=datasets, anchor=not args.no_anchor
        )
        if not certifications:
            logger.info("Al día: no hay meses nuevos para emitir.")
            continue

        for certification in certifications:
            total += 1
            logger.info(
                "V%d -> %s (%s)",
                certification.version,
                certification.cert_uid,
                certification.status,
            )

    print(f"\n{total} snapshot(s) mensual(es) emitidos.\n")


if __name__ == "__main__":
    main()
