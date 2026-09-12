"""Limpia todos los campos de prueba y efímeros de data/terria.db,

dejando únicamente los campos agrícolas reales de producción y estaciones experimentales.
"""
from __future__ import annotations

import sqlite3
from app.schemas import FieldCreate, PolygonGeometry
from app.store import get_field_store
from app.what_if.cli import PRESETS, _box_from_centroid

def clean_database() -> None:
    conn = sqlite3.connect("data/terria.db")
    cursor = conn.cursor()

    # Identificar IDs de los 3 campos reales del INTA / UNRC
    real_rows = cursor.execute(
        "SELECT id, name FROM fields WHERE name LIKE '%INTA%' OR name LIKE '%Carril%'"
    ).fetchall()
    real_ids = [row[0] for row in real_rows]
    print(f"Conservando {len(real_ids)} campos experimentales reales:")
    for r in real_rows:
        print(f"  • {r[1]} ({r[0]})")

    # Eliminar datos de prueba en tablas dependientes
    placeholders = ",".join("?" for _ in real_ids)
    cursor.execute(f"DELETE FROM field_public_timelapse WHERE field_id NOT IN ({placeholders})", real_ids)
    cursor.execute(f"DELETE FROM timelapse_datasets WHERE field_id NOT IN ({placeholders})", real_ids)
    cursor.execute(f"DELETE FROM timelapse_jobs WHERE field_id NOT IN ({placeholders})", real_ids)
    cursor.execute(f"DELETE FROM field_geometry_versions WHERE field_id NOT IN ({placeholders})", real_ids)
    cursor.execute(f"DELETE FROM fields WHERE id NOT IN ({placeholders})", real_ids)

    conn.commit()
    conn.close()

    # Cargar los 6 campos agrícolas reales de PRESETS en el store
    store = get_field_store()
    existing_names = {f.name for f in store.list()}

    for k, p in PRESETS.items():
        if p["name"] not in existing_names:
            coords = _box_from_centroid(p["lat"], p["lon"], p["ha"])
            f = store.create(
                FieldCreate(
                    name=p["name"],
                    description=p["description"],
                    boundary=PolygonGeometry(type="Polygon", coordinates=[coords]),
                    country="AR",
                    province=p.get("province", "Córdoba"),
                    locality=p.get("department", ""),
                )
            )
            print(f"  + Registrado lote real preset: {f.name} ({f.area_hectares:.1f} ha)")

    print("\n" + "=" * 80)
    print("CAMPOS REALES EN BASE DE DATOS LOCAL data/terria.db:")
    print("=" * 80)
    all_fields = store.list()
    for idx, f in enumerate(all_fields, start=1):
        print(f"  [{idx}] {f.name} ({f.area_hectares:.1f} ha) - {f.province or ''} {f.locality or ''}")
        print(f"      UUID: {f.id}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    clean_database()
