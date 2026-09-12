from __future__ import annotations

import argparse
from datetime import date
import json
import logging
import time
from uuid import UUID

from app.schemas import FieldCreate, PolygonGeometry
from app.store import SQLiteFieldStore
from app.timelapse.processing import process_timelapse_dataset
from app.timelapse.repository import timelapse_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("timelapse.cli")
store = SQLiteFieldStore()


def run_worker(once: bool = False, poll_interval: float = 2.0) -> None:
    logger.info("Starting TERRIA Timelapse Worker (once=%s)...", once)
    while True:
        claimed = timelapse_repository.claim_next_job(lease_seconds=120)
        if not claimed:
            if once:
                logger.info("No more jobs in queue. Worker exiting.")
                break
            time.sleep(poll_interval)
            continue

        job, lease_token = claimed
        logger.info("Claimed job %s for field %s", job.id, job.field_id)

        try:
            # Load field
            field = store.get(job.field_id).value
            with timelapse_repository._get_connection() as conn:
                row = conn.execute(
                    "SELECT parameters FROM timelapse_jobs WHERE id = ?", (str(job.id),)
                ).fetchone()
                params = json.loads(row["parameters"])

            start_date = date.fromisoformat(params["start_date"])
            end_date = date.fromisoformat(params["end_date"])
            layers = params.get("layers", ["rgb", "ndvi"])
            is_demo = bool(params.get("is_demo", False))

            timelapse_repository.update_job_status(
                job_id=job.id,
                status="processing",
                progress=0.3,
                lease_token=lease_token,
            )

            manifest = process_timelapse_dataset(
                field_id=field.id,
                geometry_version_id=job.geometry_version_id,
                boundary=field.boundary,
                area_hectares=field.area_hectares,
                start_date=start_date,
                end_date=end_date,
                layers=layers,
                is_demo=is_demo,
            )

            timelapse_repository.update_job_status(
                job_id=job.id,
                status="processing",
                progress=0.8,
                lease_token=lease_token,
            )

            timelapse_repository.save_dataset(manifest, job.request_hash)

            timelapse_repository.update_job_status(
                job_id=job.id,
                status=manifest.status,
                progress=1.0,
                lease_token=lease_token,
                dataset_id=manifest.dataset_id,
            )
            logger.info("Job %s completed successfully with status %s", job.id, manifest.status)

        except Exception as exc:
            logger.error("Job %s failed: %s", job.id, exc, exc_info=True)
            timelapse_repository.update_job_status(
                job_id=job.id,
                status="failed",
                progress=0.0,
                lease_token=lease_token,
                error_code="PROCESSING_ERROR",
                error_message=str(exc),
            )

        if once:
            break


def seed_demo() -> None:
    logger.info("Seeding demonstration field and datasets...")

    # 1. Create or find sample field
    fields = store.list()
    demo_field = next((f for f in fields if f.name == "Establecimiento La Posta (Demo)"), None)
    if not demo_field:
        # Field coordinates in Pergamino / Córdoba agricultural belt
        boundary = PolygonGeometry(
            type="Polygon",
            coordinates=[
                [
                    [-60.6250, -33.9100],
                    [-60.5950, -33.9100],
                    [-60.5950, -33.8850],
                    [-60.6250, -33.8850],
                    [-60.6250, -33.9100],
                ]
            ],
        )
        demo_field = store.create(
            FieldCreate(
                name="Establecimiento La Posta (Demo)",
                description="Lote agrícola de demostración con rotación soja/maíz.",
                boundary=boundary,
                province="Buenos Aires",
                locality="Pergamino",
                country="AR",
            )
        )
        logger.info("Created demo field: %s (id=%s)", demo_field.name, demo_field.id)
    else:
        logger.info("Found existing demo field: %s (id=%s)", demo_field.name, demo_field.id)

    geom_version_id = timelapse_repository.get_or_create_geometry_version(
        field_id=demo_field.id,
        boundary=demo_field.boundary,
        area_hectares=demo_field.area_hectares,
    )

    # 2. Seed Synthetic Demo dataset (with realistic crop curves, clouds, age limit gap, and PNG assets)
    demo_start = date(2024, 1, 1)
    demo_end = date(2024, 3, 31)
    req_hash_demo = timelapse_repository.compute_request_hash(
        field_id=demo_field.id,
        geometry_version_id=geom_version_id,
        start_date=demo_start,
        end_date=demo_end,
        layers=["rgb", "ndvi"],
        is_demo=True,
    )

    existing_demo = timelapse_repository.find_ready_dataset_for_hash(req_hash_demo)
    if not existing_demo:
        logger.info("Generating synthetic demo dataset (2024-01-01 to 2024-03-31)...")
        manifest_demo = process_timelapse_dataset(
            field_id=demo_field.id,
            geometry_version_id=geom_version_id,
            boundary=demo_field.boundary,
            area_hectares=demo_field.area_hectares,
            start_date=demo_start,
            end_date=demo_end,
            layers=["rgb", "ndvi"],
            is_demo=True,
        )
        timelapse_repository.save_dataset(manifest_demo, req_hash_demo)
        logger.info(
            "Synthetic demo dataset saved: %s (%d frames, %d weather days)",
            manifest_demo.dataset_id,
            len(manifest_demo.frames),
            len(manifest_demo.weather_daily),
        )
    else:
        logger.info("Synthetic demo dataset already exists: %s", existing_demo.dataset_id)

    # 3. Seed Real Weather dataset (Open-Meteo ERA5 real historical weather)
    real_start = date(2024, 1, 1)
    real_end = date(2024, 1, 31)
    req_hash_real = timelapse_repository.compute_request_hash(
        field_id=demo_field.id,
        geometry_version_id=geom_version_id,
        start_date=real_start,
        end_date=real_end,
        layers=["rgb", "ndvi"],
        is_demo=False,
    )

    existing_real = timelapse_repository.find_ready_dataset_for_hash(req_hash_real)
    if not existing_real:
        logger.info("Fetching real historical weather from Open-Meteo (2024-01-01 to 2024-01-31)...")
        manifest_real = process_timelapse_dataset(
            field_id=demo_field.id,
            geometry_version_id=geom_version_id,
            boundary=demo_field.boundary,
            area_hectares=demo_field.area_hectares,
            start_date=real_start,
            end_date=real_end,
            layers=["rgb", "ndvi"],
            is_demo=False,
        )
        timelapse_repository.save_dataset(manifest_real, req_hash_real)
        logger.info(
            "Real weather dataset saved: %s (status=%s, %d weather days)",
            manifest_real.dataset_id,
            manifest_real.status,
            len(manifest_real.weather_daily),
        )
    else:
        logger.info("Real weather dataset already exists: %s", existing_real.dataset_id)

    print("\n" + "=" * 70)
    print("DEMO SEEDING COMPLETED SUCCESSFULLY")
    print(f"Field Name: {demo_field.name}")
    print(f"Field ID:   {demo_field.id}")
    print("Datasets available:")
    for ds in timelapse_repository.list_datasets_for_field(demo_field.id):
        demo_label = "DEMO SINTÉTICA" if ds.is_demo else "DATOS REALES (Clima Open-Meteo)"
        print(f" - [{demo_label}] {ds.id}: {ds.start_date} a {ds.end_date} (Frames: {ds.frames_count}, Estado: {ds.status})")
    print("=" * 70 + "\n")


def generate(
    field_id: UUID,
    start_date: date,
    end_date: date,
    is_demo: bool = False,
) -> None:
    field = store.get(field_id).value
    geom_version_id = timelapse_repository.get_or_create_geometry_version(
        field_id=field.id,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
    )
    req_hash = timelapse_repository.compute_request_hash(
        field_id=field.id,
        geometry_version_id=geom_version_id,
        start_date=start_date,
        end_date=end_date,
        layers=["rgb", "ndvi"],
        is_demo=is_demo,
    )
    manifest = process_timelapse_dataset(
        field_id=field.id,
        geometry_version_id=geom_version_id,
        boundary=field.boundary,
        area_hectares=field.area_hectares,
        start_date=start_date,
        end_date=end_date,
        is_demo=is_demo,
    )
    timelapse_repository.save_dataset(manifest, req_hash)
    logger.info("Generated and persisted dataset %s with status %s", manifest.dataset_id, manifest.status)


def main() -> None:
    parser = argparse.ArgumentParser(description="TERRIA Timelapse Processing CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Worker command
    worker_parser = subparsers.add_parser("run-worker", help="Run the background worker")
    worker_parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    worker_parser.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds")

    # Seed command
    subparsers.add_parser("seed-demo", help="Seed a demo field with synthetic and real datasets")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Directly generate a timelapse dataset")
    gen_parser.add_argument("--field-id", type=UUID, required=True, help="Field UUID")
    gen_parser.add_argument("--start-date", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    gen_parser.add_argument("--end-date", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    gen_parser.add_argument("--demo", action="store_true", help="Generate synthetic demo dataset")

    args = parser.parse_args()

    if args.command == "run-worker":
        run_worker(once=args.once, poll_interval=args.interval)
    elif args.command == "seed-demo":
        seed_demo()
    elif args.command == "generate":
        generate(
            field_id=args.field_id,
            start_date=args.start_date,
            end_date=args.end_date,
            is_demo=args.demo,
        )


if __name__ == "__main__":
    main()
