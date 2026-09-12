from __future__ import annotations

from typing import Any

import httpx

# Matriz geográfica de contingencia offline para las principales regiones agrícolas argentinas
REGIONAL_DEPARTMENTS_DB: list[dict[str, Any]] = [
    # Entre Ríos
    {
        "province": "Entre Rios",
        "department": "Federacion",
        "region": "Mesopotamia",
        "bbox": [-58.9, -31.3, -57.7, -30.3],
        "soil": {
            "order": "Vertisol",
            "clay_pct": 42.0,
            "sand_pct": 14.0,
            "silt_pct": 44.0,
            "class": "Arcillo Limoso (Vertisol Peludal)",
        },
    },
    {
        "province": "Entre Rios",
        "department": "Concordia",
        "region": "Mesopotamia",
        "bbox": [-58.7, -31.8, -57.8, -31.1],
        "soil": {
            "order": "Vertisol",
            "clay_pct": 40.0,
            "sand_pct": 18.0,
            "silt_pct": 42.0,
            "class": "Franco Arcillo Limoso",
        },
    },
    {
        "province": "Entre Rios",
        "department": "Gualeguaychu",
        "region": "Mesopotamia",
        "bbox": [-59.3, -33.4, -58.2, -32.6],
        "soil": {
            "order": "Vertisol / Molisol",
            "clay_pct": 36.0,
            "sand_pct": 20.0,
            "silt_pct": 44.0,
            "class": "Franco Arcillo Limoso",
        },
    },
    # Córdoba
    {
        "province": "Cordoba",
        "department": "Marcos Juarez",
        "region": "Zona Nucleo / Pampa Humeda",
        "bbox": [-62.7, -33.4, -61.5, -32.2],
        "soil": {
            "order": "Argiudol",
            "clay_pct": 24.2,
            "sand_pct": 17.8,
            "silt_pct": 58.0,
            "class": "Franco Limoso (Argiudol Tipico)",
        },
    },
    {
        "province": "Cordoba",
        "department": "Rio Cuarto",
        "region": "Pampa Arenosa Cordobesa",
        "bbox": [-65.3, -34.0, -63.8, -32.6],
        "soil": {
            "order": "Hapludol",
            "clay_pct": 15.0,
            "sand_pct": 54.0,
            "silt_pct": 31.0,
            "class": "Franco Arenoso (Hapludol Entico)",
        },
    },
    {
        "province": "Cordoba",
        "department": "Union",
        "region": "Pampa Humeda",
        "bbox": [-63.2, -33.3, -62.3, -32.2],
        "soil": {
            "order": "Argiudol",
            "clay_pct": 23.0,
            "sand_pct": 22.0,
            "silt_pct": 55.0,
            "class": "Franco Limoso",
        },
    },
    # Buenos Aires
    {
        "province": "Buenos Aires",
        "department": "Pergamino",
        "region": "Pampa Ondulada / Zona Nucleo",
        "bbox": [-61.0, -34.2, -60.2, -33.6],
        "soil": {
            "order": "Argiudol",
            "clay_pct": 26.0,
            "sand_pct": 15.0,
            "silt_pct": 59.0,
            "class": "Franco Limoso (Argiudol Tipico Serie Pergamino)",
        },
    },
    {
        "province": "Buenos Aires",
        "department": "Rojas",
        "region": "Pampa Ondulada",
        "bbox": [-61.2, -34.5, -60.6, -34.0],
        "soil": {
            "order": "Argiudol",
            "clay_pct": 25.5,
            "sand_pct": 16.5,
            "silt_pct": 58.0,
            "class": "Franco Limoso",
        },
    },
    {
        "province": "Buenos Aires",
        "department": "Tres Arroyos",
        "region": "Pampa Austral / Fina",
        "bbox": [-60.9, -38.9, -59.7, -38.0],
        "soil": {
            "order": "Argiudol / Paleudol con tosca",
            "clay_pct": 22.0,
            "sand_pct": 32.0,
            "silt_pct": 46.0,
            "class": "Franco (Suelo Somero con Tosca)",
        },
    },
    # Santa Fe
    {
        "province": "Santa Fe",
        "department": "General Lopez",
        "region": "Zona Nucleo Venado Tuerto",
        "bbox": [-62.4, -34.5, -61.2, -33.4],
        "soil": {
            "order": "Hapludol / Argiudol",
            "clay_pct": 22.0,
            "sand_pct": 28.0,
            "silt_pct": 50.0,
            "class": "Franco Limoso",
        },
    },
    {
        "province": "Santa Fe",
        "department": "Caseros",
        "region": "Zona Nucleo Casilda",
        "bbox": [-62.0, -33.4, -61.0, -32.8],
        "soil": {
            "order": "Argiudol",
            "clay_pct": 25.0,
            "sand_pct": 16.0,
            "silt_pct": 59.0,
            "class": "Franco Limoso",
        },
    },
]


def resolve_territorial_context(lat: float, lon: float) -> dict[str, Any]:
    """Geocodifica coordenadas para obtener Departamento, Provincia y perfil edafológico zonal.

    Consulta OpenStreetMap Nominatim y cuenta con fallback a matriz regional offline.
    """
    resolved_dept: str | None = None
    resolved_prov: str | None = None

    # 1. Geocodificación inversa con Nominatim vía httpx
    try:
        headers = {"User-Agent": "TERRIA-WhatIf/2.1 (agro-engine@terria.ag)"}
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
        with httpx.Client(timeout=3.5) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 200:
                addr = r.json().get("address", {})
                resolved_prov = addr.get("state")
                county = addr.get("county") or addr.get("state_district") or ""
                if "departamento" in county.lower():
                    resolved_dept = county.lower().replace("departamento", "").strip().title()
                elif "partido" in county.lower():
                    resolved_dept = county.lower().replace("partido", "").strip().title()
                elif county:
                    resolved_dept = county.title()
    except Exception:
        pass

    # 2. Comprobación espacial con la matriz regional offline
    matched_entry: dict[str, Any] | None = None
    for entry in REGIONAL_DEPARTMENTS_DB:
        b = entry["bbox"]
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
            matched_entry = entry
            break

    if not resolved_prov and matched_entry:
        resolved_prov = matched_entry["province"]
    if not resolved_dept and matched_entry:
        resolved_dept = matched_entry["department"]

    # Fallback general si está fuera de las matrices
    prov = resolved_prov or "Cordoba"
    dept = resolved_dept or "Marcos Juarez"
    region = matched_entry["region"] if matched_entry else "Region Pampeana Central"
    soil_base = (
        matched_entry["soil"]
        if matched_entry
        else {
            "order": "Molisol / Argiudol",
            "clay_pct": 24.0,
            "sand_pct": 20.0,
            "silt_pct": 56.0,
            "class": "Franco Limoso",
        }
    )

    return {
        "department": dept,
        "province": prov,
        "region": region,
        "soil_baseline": soil_base,
        "citation": f"Dpto. {dept}, {prov} ({region})",
    }
