"""Carga los 3 campos reales de demostración en la base configurada.

Uso:
    uv run python scripts/seed_real_fields.py

Por cada campo (idempotente por nombre):
  1. Crea el field vía get_field_store() (Supabase si DATABASE_URL, si no SQLite).
  2. Encola un job de timelapse REAL (is_demo=False, campaña 2024/25) y lo
     procesa con el worker — clima Open-Meteo + Sentinel-2 vía CDSE si hay
     credenciales (si no, dataset 'partial' con clima real).
  3. Publica el field y el dataset → ficha pública lista para el frontend.

Campos elegidos (ver investigación en cerebro compartido): tres
establecimientos experimentales públicos de Córdoba, en departamentos con
valores de tierra diferenciados (IDECOR) y rotaciones documentadas.
"""

from __future__ import annotations

from datetime import date
import logging

from app.schemas import FieldCreate, PolygonGeometry
from app.store import get_field_store
from app.timelapse.cli import run_worker
from app.timelapse.repository import get_timelapse_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("seed_real_fields")

# Campaña agrícola 2024/25 (siembra oct-nov → cosecha mar-abr).
TIMELAPSE_START = date(2024, 10, 1)
TIMELAPSE_END = date(2025, 4, 30)
TIMELAPSE_LAYERS = ["rgb", "ndvi"]

REAL_FIELDS: list[dict] = [
    {
        # Hero: dto. Marcos Juárez = mayor valor de tierra de Córdoba (IDECOR),
        # máxima densidad de lotes gemelos en 50 km, rotación soja-maíz clásica.
        "name": "Lote Sur — EEA INTA Marcos Juárez",
        "description": (
            "Lote agrícola dentro del predio de la Estación Experimental "
            "Agropecuaria INTA Marcos Juárez (Ruta Provincial 12 km 3), núcleo "
            "agrícola-ganadero del sudeste cordobés. Suelo Argiudol típico, "
            "Clase I. Ensayos de larga duración de rotaciones soja-maíz con "
            "cultivos de cobertura."
        ),
        "country": "AR",
        "province": "Córdoba",
        "locality": "Marcos Juárez",
        "coordinates": [
            [
                [-62.1013, -32.7057],
                [-62.0907, -32.7057],
                [-62.0907, -32.7193],
                [-62.1013, -32.7193],
                [-62.1013, -32.7057],
            ]
        ],
    },
    {
        # Rotación más variada (maní, sorgo, girasol) → what-if más rico;
        # RN 9 sobre el lote para el driver logístico de futurología.
        "name": "Lote NO — EEA INTA Manfredi",
        "description": (
            "Lote agrícola dentro del predio de la EEA INTA Manfredi "
            "(RN 9 km 636), una de las estaciones experimentales más antiguas "
            "del país (1928). Ensayo de referencia regional de labranzas y "
            "secuencias soja-maíz desde 1997 sobre Haplustol típico."
        ),
        "country": "AR",
        "province": "Córdoba",
        "locality": "Manfredi",
        "coordinates": [
            [
                [-63.7673, -31.8161],
                [-63.7567, -31.8161],
                [-63.7567, -31.8279],
                [-63.7673, -31.8279],
                [-63.7673, -31.8161],
            ]
        ],
    },
    {
        # Piedemonte de Comechingones: estación meteorológica in-situ, ensayo
        # de rotaciones agrícola-ganaderas desde 1994 (mix agro-ganadero).
        "name": "Campo Experimental Pozo del Carril (FAV-UNRC)",
        "description": (
            "Establecimiento experimental de ~200 ha de la Facultad de "
            "Agronomía y Veterinaria (UNRC) en La Aguada, piedemonte de "
            "Comechingones. Ensayo de larga duración de rotaciones "
            "agrícola-ganaderas desde 1994, sistema silvopastoril y estación "
            "meteorológica automática integrada a la red provincial."
        ),
        "country": "AR",
        "province": "Córdoba",
        "locality": "La Aguada",
        "coordinates": [
            [
                [-64.6120, -32.9619],
                [-64.5950, -32.9619],
                [-64.5950, -32.9731],
                [-64.6120, -32.9731],
                [-64.6120, -32.9619],
            ]
        ],
    },
]


def main() -> None:
    store = get_field_store()
    repo = get_timelapse_repository()
    existing = {f.name: f for f in store.list()}

    for spec in REAL_FIELDS:
        field = existing.get(spec["name"])
        if field is None:
            field = store.create(
                FieldCreate(
                    name=spec["name"],
                    description=spec["description"],
                    boundary=PolygonGeometry(
                        type="Polygon", coordinates=spec["coordinates"]
                    ),
                    country=spec["country"],
                    province=spec["province"],
                    locality=spec["locality"],
                )
            )
            logger.info("Created %s (id=%s, %.1f ha)", field.name, field.id, field.area_hectares)
        else:
            logger.info("Field %s already exists (id=%s)", field.name, field.id)

        geom_version_id = repo.get_or_create_geometry_version(
            field_id=field.id,
            boundary=field.boundary,
            area_hectares=field.area_hectares,
        )
        req_hash = repo.compute_request_hash(
            field_id=field.id,
            geometry_version_id=geom_version_id,
            start_date=TIMELAPSE_START,
            end_date=TIMELAPSE_END,
            layers=TIMELAPSE_LAYERS,
            is_demo=False,
        )
        if repo.find_ready_dataset_for_hash(req_hash):
            logger.info("Timelapse already generated for %s", field.name)
        else:
            if not repo.find_active_job(req_hash):
                job = repo.create_job(
                    field_id=field.id,
                    geometry_version_id=geom_version_id,
                    request_hash=req_hash,
                    parameters={
                        "start_date": TIMELAPSE_START.isoformat(),
                        "end_date": TIMELAPSE_END.isoformat(),
                        "layers": TIMELAPSE_LAYERS,
                        "is_demo": False,
                    },
                )
                logger.info("Queued timelapse job %s for %s", job.id, field.name)

        published = store.publish(field.id)
        logger.info("Published %s → /v1/public/fields/%s", field.name, published.public_slug)

    logger.info("Processing job queue...")
    # run_worker(once=True) procesa un job por llamada: una pasada por campo.
    for _ in REAL_FIELDS:
        run_worker(once=True, poll_interval=1.0)

    for spec in REAL_FIELDS:
        field = next(f for f in store.list() if f.name == spec["name"])
        datasets = repo.list_datasets_for_field(field.id)
        if datasets:
            repo.publish_dataset(field_id=field.id, dataset_id=datasets[0].id)
            logger.info(
                "Published dataset %s (%s, %d frames) for %s",
                datasets[0].id, datasets[0].status, datasets[0].frames_count, field.name,
            )

    print("\n" + "=" * 70)
    print("REAL FIELDS LOADED")
    for spec in REAL_FIELDS:
        field = next(f for f in store.list() if f.name == spec["name"])
        print(f"  {field.name} | {field.area_hectares} ha | /v1/public/fields/{field.public_slug}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
