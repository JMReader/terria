"""Regenera el timelapse de campaña completa (catálogo CDSE paginado) para los
campos reales, publica el dataset nuevo y opcionalmente emite una certificación.

Fuentes de datos reales (las acordadas): Sentinel-2 L2A vía Copernicus Data
Space (CDSE, catálogo paginado) + clima Open-Meteo (ERA5 reanalysis).

Uso:
    uv run python scripts/backfill_campaigns.py                     # campaña 2024/25 (default)
    uv run python scripts/backfill_campaigns.py --campaign 2025/26  # campaña 2025/26
    uv run python scripts/backfill_campaigns.py --start 2025-10-01 --end 2026-04-30
    uv run python scripts/backfill_campaigns.py --campaign 2025/26 --name Marcos
    uv run python scripts/backfill_campaigns.py --campaign 2025/26 --certify

El `request_hash` incluye la `processing_version`, así que al haberla subido a
0.3.0 se genera un dataset nuevo en lugar de reusar el recortado anterior.
"""

from __future__ import annotations

import argparse
from datetime import date
import logging
import re

from app.blockchain.service import issue_certification
from app.store import get_field_store
from app.timelapse.cli import run_worker
from app.timelapse.repository import get_timelapse_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backfill_campaigns")

# Campaña agrícola 2024/25 completa (siembra oct → cosecha abr) — default.
DEFAULT_START = date(2024, 10, 1)
DEFAULT_END = date(2025, 4, 30)
LAYERS = ["rgb", "ndvi"]


def parse_campaign(value: str) -> tuple[date, date]:
    """`YYYY/YY` (o `YYYY/YYYY`) → (1 oct del primer año, 30 abr del siguiente)."""
    match = re.fullmatch(r"(\d{4})/(\d{2}|\d{4})", value.strip())
    if match is None:
        raise argparse.ArgumentTypeError(
            "Campaña inválida: usar YYYY/YY (ej. 2025/26)"
        )
    start_year = int(match.group(1))
    tail = match.group(2)
    if len(tail) == 2:
        expected = f"{(start_year + 1) % 100:02d}"
        if tail != expected:
            raise argparse.ArgumentTypeError(
                f"El segundo año de {value} debe ser {expected} (año siguiente)"
            )
        end_year = start_year + 1
    else:
        end_year = int(tail)
        if end_year != start_year + 1:
            raise argparse.ArgumentTypeError(
                f"El segundo año de {value} debe ser {start_year + 1} (año siguiente)"
            )
    return date(start_year, 10, 1), date(end_year, 4, 30)


def backfill_field(field, repo, certify: bool, start: date, end: date) -> None:
    logger.info("=== %s | campaña %s → %s ===", field.name, start, end)

    geometry_version_id = repo.get_or_create_geometry_version(
        field_id=field.id,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
    )
    request_hash = repo.compute_request_hash(
        field_id=field.id,
        geometry_version_id=geometry_version_id,
        start_date=start,
        end_date=end,
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
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
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
            period_from=start.year,
            period_to=end.year,
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
    parser.add_argument(
        "--campaign",
        type=parse_campaign,
        default=None,
        metavar="YYYY/YY",
        help="Campaña agrícola (ej. 2025/26); default 2024/25",
    )
    parser.add_argument("--start", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--certify", action="store_true", help="Emitir certificación tras publicar")
    args = parser.parse_args()

    start, end = args.campaign or (DEFAULT_START, DEFAULT_END)
    start = args.start or start
    end = args.end or end
    if start > end:
        parser.error("--start no puede ser posterior a --end")

    store = get_field_store()
    repo = get_timelapse_repository()

    fields = store.list()
    if args.name:
        fields = [field for field in fields if args.name.lower() in field.name.lower()]
    if not fields:
        raise SystemExit("No hay campos que coincidan con el filtro.")

    logger.info("Backfill de %d campo(s): %s → %s", len(fields), start, end)
    for field in fields:
        backfill_field(field, repo, args.certify, start, end)

    print("\nBackfill completado.\n")


if __name__ == "__main__":
    main()
