"""Regenera el timelapse de campaña completa (catálogo CDSE paginado) para los
campos reales, publica el dataset nuevo y opcionalmente emite una certificación.

Uso:
    uv run python scripts/backfill_campaigns.py                 # los 3 campos, sin certificar
    uv run python scripts/backfill_campaigns.py --name Marcos   # sólo uno
    uv run python scripts/backfill_campaigns.py --certify       # además emite V(n+1)

El `request_hash` incluye la `processing_version`, así que al haberla subido a
0.3.0 se genera un dataset nuevo en lugar de reusar el recortado anterior.
"""

from __future__ import annotations

import argparse
from datetime import date
import logging

from app.blockchain.service import issue_certification
from app.store import get_field_store
from app.timelapse.cli import run_worker
from app.timelapse.repository import get_timelapse_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backfill_campaigns")

# Campaña agrícola 2024/25 completa (siembra oct → cosecha abr).
START = date(2024, 10, 1)
END = date(2025, 4, 30)
LAYERS = ["rgb", "ndvi"]


def backfill_field(field, repo, certify: bool) -> None:
    logger.info("=== %s ===", field.name)

    geometry_version_id = repo.get_or_create_geometry_version(
        field_id=field.id,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
    )
    request_hash = repo.compute_request_hash(
        field_id=field.id,
        geometry_version_id=geometry_version_id,
        start_date=START,
        end_date=END,
        layers=LAYERS,
        is_demo=False,
    )

    manifest = repo.find_ready_dataset_for_hash(request_hash)
    if manifest is None:
        if not repo.find_active_job(request_hash):
            repo.create_job(
                field_id=field.id,
                geometry_version_id=geometry_version_id,
                request_hash=request_hash,
                parameters={
                    "start_date": START.isoformat(),
                    "end_date": END.isoformat(),
                    "layers": LAYERS,
                    "is_demo": False,
                },
            )
        logger.info("Procesando campaña completa (puede tardar varios minutos)...")
        run_worker(once=True, poll_interval=1.0)
        manifest = repo.find_ready_dataset_for_hash(request_hash)

    if manifest is None:
        logger.error("No se pudo generar el dataset para %s", field.name)
        return

    fechas = sorted(frame.local_date.isoformat() for frame in manifest.frames)
    range_msg = f"{fechas[0]} → {fechas[-1]}" if fechas else "sin frames"
    logger.info(
        "Dataset %s | status=%s | frames=%d | rango=%s",
        manifest.dataset_id,
        manifest.status,
        len(manifest.frames),
        range_msg,
    )

    repo.publish_dataset(field_id=field.id, dataset_id=manifest.dataset_id)
    logger.info("Dataset publicado")

    if certify:
        datasets = [
            dataset
            for dataset in repo.list_datasets_for_field(field.id)
            if dataset.id == manifest.dataset_id
        ]
        certification = issue_certification(
            field=field,
            datasets=datasets,
            period_from=START.year,
            period_to=END.year,
            anchor=True,
        )
        logger.info(
            "Certificación V%d emitida: %s (%s)",
            certification.version,
            certification.cert_uid,
            certification.status,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill de campaña completa para los campos reales.")
    parser.add_argument("--name", default=None, help="Filtro por nombre de campo (substring)")
    parser.add_argument("--certify", action="store_true", help="Emitir certificación tras publicar")
    args = parser.parse_args()

    store = get_field_store()
    repo = get_timelapse_repository()

    fields = store.list()
    if args.name:
        fields = [field for field in fields if args.name.lower() in field.name.lower()]
    if not fields:
        raise SystemExit("No hay campos que coincidan con el filtro.")

    for field in fields:
        backfill_field(field, repo, args.certify)

    print("\nBackfill completado.\n")


if __name__ == "__main__":
    main()
