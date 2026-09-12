"""Seed demo local para el Pasaporte Digital de Parcela.

Crea el owner demo y 4 parcelas con boundaries poligonales (una publicada).
Idempotente: re-ejecutar no duplica owners ni parcelas.

SOLO corre contra el SQLite local — con Supabase activo se niega (allowlist
cerrada de los 3 campos reales, ver AGENTS.md).

Uso:
    uv run python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import EmailTaken, LoginRequest, RegisterRequest, auth_store  # noqa: E402
from app.config import settings  # noqa: E402
from app.schemas import FieldCreate  # noqa: E402
from app.store import get_field_store  # noqa: E402

DEMO_EMAIL = "dueno@terria.dev"
DEMO_PASSWORD = "terria1234"
DEMO_NAME = "Dueño Demo"

# Polígonos aproximados alrededor de centroides de campos del mock frontend.
DEMO_FIELDS = [
    {
        "name": "Lote 'La Esperanza' — Av. 11 de Septiembre",
        "province": "Córdoba",
        "locality": "Coronel Olmedo",
        "description": "Establecimiento agropecuario sobre Av. 11 de Septiembre con lotes delimitados por caminos rurales. Rotación maíz/soja de alto rendimiento y napa freática en cota estival.",
        "boundary": [
            [-64.160, -31.512],
            [-64.118, -31.505],
            [-64.109, -31.488],
            [-64.121, -31.469],
            [-64.156, -31.476],
            [-64.168, -31.498],
            [-64.160, -31.512],
        ],
        "publish": True,
    },
    {
        "name": "Establecimiento 'Don Pedro'",
        "province": "Buenos Aires",
        "locality": "Pergamino",
        "description": "Campo de máxima productividad en la Zona Núcleo de Pergamino. Argiudoles profundos sin limitantes, 300 mm de agua útil.",
        "boundary": [
            [-60.512, -33.972],
            [-60.466, -33.968],
            [-60.458, -33.944],
            [-60.472, -33.921],
            [-60.515, -33.928],
            [-60.524, -33.953],
            [-60.512, -33.972],
        ],
        "publish": False,
    },
    {
        "name": "Campo 'El Ombú'",
        "province": "Santa Fe",
        "locality": "Venado Tuerto",
        "description": "Lote tecnificado en el cinturón agrícola de Venado Tuerto con infraestructura completa para almacenamiento y monitoreo.",
        "boundary": [
            [-61.892, -33.801],
            [-61.845, -33.796],
            [-61.838, -33.772],
            [-61.852, -33.752],
            [-61.889, -33.758],
            [-61.899, -33.784],
            [-61.892, -33.801],
        ],
        "publish": False,
    },
    {
        "name": "Finca 'San Jerónimo'",
        "province": "Córdoba",
        "locality": "Villa María",
        "description": "Campo mixto con 280 ha bajo riego por pivote central. Garantía de rendimiento aun en campañas de déficit hídrico.",
        "boundary": [
            [-63.172, -32.378],
            [-63.126, -32.371],
            [-63.118, -32.348],
            [-63.135, -32.326],
            [-63.172, -32.333],
            [-63.181, -32.358],
            [-63.172, -32.378],
        ],
        "publish": False,
    },
]


def main() -> None:
    if settings.use_supabase:
        sys.exit(
            "ERROR: DATABASE_URL configurada — este seed es solo para el SQLite "
            "local. En Supabase solo existen los 3 campos reales (ver AGENTS.md)."
        )
    store = get_field_store()

    try:
        auth = auth_store.register(
            RegisterRequest(email=DEMO_EMAIL, password=DEMO_PASSWORD, name=DEMO_NAME)
        )
        owner = auth.owner
        print(f"✓ Owner creado: {owner.email} ({owner.id})")
    except EmailTaken:
        # Ya existe — recuperamos el owner via login
        owner = auth_store.login(
            LoginRequest(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        ).owner
        print(f"· Owner ya existía: {owner.email} ({owner.id})")

    existing = {f.name for f in store.list_by_owner(owner.id)}
    created = 0
    for spec in DEMO_FIELDS:
        if spec["name"] in existing:
            print(f"· Parcela ya cargada: {spec['name']}")
            continue
        field = store.create(
            FieldCreate(
                name=spec["name"],
                description=spec["description"],
                boundary={"type": "Polygon", "coordinates": [spec["boundary"]]},
                province=spec["province"],
                locality=spec["locality"],
            ),
            owner_id=owner.id,
        )
        created += 1
        if spec["publish"]:
            field = store.publish(field.id)
            print(f"✓ Parcela creada y PUBLICADA: {field.name} → /p/{field.public_slug}")
        else:
            print(f"✓ Parcela creada: {field.name}")

    fields = store.list_by_owner(owner.id)
    print(f"\nResumen: {len(fields)} parcelas del owner ({created} nuevas)")
    for f in fields:
        state = f"pública /p/{f.public_slug}" if f.visibility == "public" else "privada"
        print(f"  - {f.name} [{f.area_hectares} ha] — {state}")
    print(f"\nLogin demo: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
