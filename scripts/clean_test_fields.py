"""Limpia todos los campos de prueba y efímeros de data/terria.db,

dejando únicamente los campos agrícolas reales de producción y estaciones experimentales.
"""
from __future__ import annotations

import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    # Recalcular y persistir hectáreas geodésicas reales con Shoelace
    from app.what_if.geometry import calculate_shoelace_area_ha
    import json

    for r in real_rows:
        f_id, f_name = r[0], r[1]
        b_raw = cursor.execute("SELECT boundary FROM fields WHERE id = ?", (f_id,)).fetchone()[0]
        b_data = json.loads(b_raw)
        ring = b_data.get("coordinates", [[]])[0]
        real_ha = calculate_shoelace_area_ha(ring)
        cursor.execute("UPDATE fields SET area_hectares = ? WHERE id = ?", (real_ha, f_id))
        cursor.execute("UPDATE field_geometry_versions SET area_hectares = ? WHERE field_id = ?", (real_ha, f_id))
        print(f"  ✓ Hectáreas reales actualizadas para '{f_name}': {real_ha:.2f} ha")

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("CAMPOS REALES EN BASE DE DATOS LOCAL data/terria.db (EXACTAMENTE 3):")
    print("=" * 80)
    store = get_field_store()
    all_fields = store.list()
    for idx, f in enumerate(all_fields, start=1):
        print(f"  [{idx}] {f.name} ({f.area_hectares:.1f} ha) - {f.province or ''} {f.locality or ''}")
        print(f"      UUID: {f.id}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    clean_database()
