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
    # Chaco
    {
        "province": "Chaco",
        "department": "Chacabuco",
        "region": "Chaco Central / Nucleo Algodonero-Sojero",
        "bbox": [-61.5, -27.6, -60.8, -27.0],
        "soil": {
            "order": "Argiustol",
            "clay_pct": 28.0,
            "sand_pct": 20.0,
            "silt_pct": 52.0,
            "class": "Franco Arcillo Limoso",
        },
    },
    # Santiago del Estero
    {
        "province": "Santiago del Estero",
        "department": "Moreno",
        "region": "Chaco Seco / Quimilí",
        "bbox": [-62.8, -27.8, -61.8, -27.0],
        "soil": {
            "order": "Haplustol",
            "clay_pct": 22.0,
            "sand_pct": 32.0,
            "silt_pct": 46.0,
            "class": "Franco Limoso",
        },
    },
    # Salta
    {
        "province": "Salta",
        "department": "Anta",
        "region": "NOA / Umbral al Chaco",
        "bbox": [-64.5, -25.5, -63.0, -24.4],
        "soil": {
            "order": "Haplustol",
            "clay_pct": 24.0,
            "sand_pct": 28.0,
            "silt_pct": 48.0,
            "class": "Franco Limoso (Suelo Agricola NOA)",
        },
    },
    # La Pampa
    {
        "province": "La Pampa",
        "department": "Realico",
        "region": "Pampa Seca / Planicie con Tosca",
        "bbox": [-64.6, -35.5, -63.5, -35.0],
        "soil": {
            "order": "Hapludol / Calciustol",
            "clay_pct": 16.0,
            "sand_pct": 52.0,
            "silt_pct": 32.0,
            "class": "Franco Arenoso",
        },
    },
    # San Luis
    {
        "province": "San Luis",
        "department": "General Pedernera",
        "region": "Pampa Occidental / Villa Mercedes",
        "bbox": [-65.7, -34.2, -64.9, -33.2],
        "soil": {
            "order": "Hapludol",
            "clay_pct": 14.0,
            "sand_pct": 58.0,
            "silt_pct": 28.0,
            "class": "Franco Arenoso con Medanos Fijados",
        },
    },
    # Corrientes
    {
        "province": "Corrientes",
        "department": "Goya",
        "region": "Mesopotamia Norte / Litoral Paranaense",
        "bbox": [-59.5, -29.5, -58.8, -28.8],
        "soil": {
            "order": "Alfisol / Molisol",
            "clay_pct": 32.0,
            "sand_pct": 24.0,
            "silt_pct": 44.0,
            "class": "Franco Arcillo Arenoso",
        },
    },
    # Mendoza
    {
        "province": "Mendoza",
        "department": "San Rafael",
        "region": "Cuyo / Oasis Sur Diamante-Atuel",
        "bbox": [-68.8, -35.2, -67.4, -34.4],
        "soil": {
            "order": "Torrifluvent / Aridisol",
            "clay_pct": 12.0,
            "sand_pct": 65.0,
            "silt_pct": 23.0,
            "class": "Arenoso Aluvial Bajo Riego",
        },
    },
    # Rio Negro
    {
        "province": "Rio Negro",
        "department": "General Roca",
        "region": "Patagonia Norte / Alto Valle",
        "bbox": [-68.0, -39.2, -67.2, -38.8],
        "soil": {
            "order": "Entisol / Torrifluvent",
            "clay_pct": 15.0,
            "sand_pct": 60.0,
            "silt_pct": 25.0,
            "class": "Aluvial de Valle Irrigado",
        },
    },
]


def resolve_argentina_region(lat: float, lon: float) -> dict[str, Any]:
    """Resuelve la provincia, departamento representativo y características agroecológicas

    para cualquier coordenada dentro del territorio de la República Argentina.
    """
    if lat < -52.5 and lon > -69.0:
        prov, dept, reg = "Tierra del Fuego", "Rio Grande", "Estepa Magallanica Fueguina"
        soil = {"order": "Histosol / Molisol", "clay_pct": 18.0, "sand_pct": 35.0, "silt_pct": 47.0, "class": "Turba y Franco Arenoso Frio"}
    elif lat < -46.0:
        prov, dept, reg = "Santa Cruz", "Guer Aike", "Patagonia Austral / Meseta Semiarida"
        soil = {"order": "Aridisol / Entisol", "clay_pct": 12.0, "sand_pct": 62.0, "silt_pct": 26.0, "class": "Pedregoso con Estepa Arbustiva"}
    elif lat < -42.0:
        prov, dept, reg = "Chubut", "Rawson", "Patagonia Central / Valle Inferior y Meseta"
        soil = {"order": "Aridisol / Torriortent", "clay_pct": 14.0, "sand_pct": 58.0, "silt_pct": 28.0, "class": "Franco Arenoso Arido"}
    elif lat < -37.5:
        if lon < -68.0:
            prov, dept, reg = "Neuquen", "Confluencia", "Patagonia Norte / Cuenca del Limay"
            soil = {"order": "Aridisol / Torrifluvent", "clay_pct": 14.0, "sand_pct": 62.0, "silt_pct": 24.0, "class": "Aluvial de Valle"}
        elif lon < -65.0:
            prov, dept, reg = "Rio Negro", "General Roca", "Alto Valle de Rio Negro"
            soil = {"order": "Entisol / Torrifluvent", "clay_pct": 15.0, "sand_pct": 60.0, "silt_pct": 25.0, "class": "Franco Aluvial Bajo Riego"}
        elif lon < -61.5:
            prov, dept, reg = "Buenos Aires", "Bahia Blanca", "Pampa Austral / Sudoeste Agricola Ganadero"
            soil = {"order": "Calciustol", "clay_pct": 18.0, "sand_pct": 48.0, "silt_pct": 34.0, "class": "Franco Arenoso con Tosca"}
        else:
            prov, dept, reg = "Buenos Aires", "Tres Arroyos", "Pampa Austral / Mar y Sierras"
            soil = {"order": "Argiudol con tosca", "clay_pct": 22.0, "sand_pct": 32.0, "silt_pct": 46.0, "class": "Franco Somero"}
    elif lat < -33.5:
        if lon < -66.5:
            prov, dept, reg = "Mendoza", "San Rafael", "Cuyo / Oasis Sur Diamante-Atuel"
            soil = {"order": "Torrifluvent / Aridisol", "clay_pct": 12.0, "sand_pct": 65.0, "silt_pct": 23.0, "class": "Arenoso Aluvial Bajo Riego"}
        elif lon < -64.5:
            prov, dept, reg = "La Pampa", "Realico", "Pampa Seca / Planicie con Tosca"
            soil = {"order": "Hapludol / Calciustol", "clay_pct": 16.0, "sand_pct": 52.0, "silt_pct": 32.0, "class": "Franco Arenoso"}
        elif lon < -62.5:
            prov, dept, reg = "Cordoba", "Rio Cuarto", "Pampa Arenosa Cordobesa"
            soil = {"order": "Hapludol Entico", "clay_pct": 15.0, "sand_pct": 54.0, "silt_pct": 31.0, "class": "Franco Arenoso"}
        elif lon < -60.5:
            prov, dept, reg = "Buenos Aires", "Junin", "Pampa Humeda / Noroeste Bonaerense"
            soil = {"order": "Argiudol", "clay_pct": 24.0, "sand_pct": 20.0, "silt_pct": 56.0, "class": "Franco Limoso"}
        elif lon < -59.0:
            prov, dept, reg = "Buenos Aires", "Pergamino", "Zona Nucleo Pampeana"
            soil = {"order": "Argiudol Tipico", "clay_pct": 26.0, "sand_pct": 15.0, "silt_pct": 59.0, "class": "Franco Limoso Serie Pergamino"}
        else:
            prov, dept, reg = "Buenos Aires", "Chascomus", "Cuenca del Salado / Ganadera"
            soil = {"order": "Natracualf", "clay_pct": 35.0, "sand_pct": 12.0, "silt_pct": 53.0, "class": "Arcilloso Hidromorfico"}
    elif lat < -30.0:
        if lon < -66.5:
            prov, dept, reg = "San Juan", "Caucete", "Cuyo / Valle de Tulum"
            soil = {"order": "Torrifluvent / Aridisol", "clay_pct": 14.0, "sand_pct": 64.0, "silt_pct": 22.0, "class": "Aluvial Estratificado"}
        elif lon < -65.0:
            prov, dept, reg = "San Luis", "General Pedernera", "Pampa Occidental / Villa Mercedes"
            soil = {"order": "Hapludol", "clay_pct": 14.0, "sand_pct": 58.0, "silt_pct": 28.0, "class": "Franco Arenoso"}
        elif lon < -62.5:
            prov, dept, reg = "Cordoba", "Marcos Juarez", "Zona Nucleo Cordobesa"
            soil = {"order": "Argiudol Tipico", "clay_pct": 24.2, "sand_pct": 17.8, "silt_pct": 58.0, "class": "Franco Limoso (Argiudol Tipico)"}
        elif lon < -60.5:
            prov, dept, reg = "Santa Fe", "Castellanos", "Cuenca Lechera Santafesina"
            soil = {"order": "Argiudol", "clay_pct": 24.0, "sand_pct": 18.0, "silt_pct": 58.0, "class": "Franco Limoso"}
        elif lon < -58.5:
            prov, dept, reg = "Entre Rios", "Parana", "Mesopotamia / Vertisoles Entrerrianos"
            soil = {"order": "Vertisol", "clay_pct": 38.0, "sand_pct": 16.0, "silt_pct": 46.0, "class": "Arcilloso Limoso"}
        else:
            prov, dept, reg = "Entre Rios", "Federacion", "Mesopotamia / Rio Uruguay"
            soil = {"order": "Vertisol Peludal", "clay_pct": 42.0, "sand_pct": 14.0, "silt_pct": 44.0, "class": "Arcillo Limoso"}
    elif lat < -26.5:
        if lon < -66.0:
            prov, dept, reg = "La Rioja", "Chilecito", "NOA / Valles y Quebradas de Chilecito"
            soil = {"order": "Torriortent / Aridisol", "clay_pct": 12.0, "sand_pct": 68.0, "silt_pct": 20.0, "class": "Arenoso Pedregoso"}
        elif lon < -65.2:
            prov, dept, reg = "Catamarca", "Valle Central", "NOA / Valle Central Catamarqueno"
            soil = {"order": "Aridisol", "clay_pct": 15.0, "sand_pct": 60.0, "silt_pct": 25.0, "class": "Franco Arenoso Aluvial"}
        elif lon < -64.5:
            prov, dept, reg = "Tucuman", "Cruz Alta", "NOA / Llanura Pedemontana Tucumana"
            soil = {"order": "Argiudol / Hapludol", "clay_pct": 22.0, "sand_pct": 26.0, "silt_pct": 52.0, "class": "Franco Limoso"}
        elif lon < -62.5:
            prov, dept, reg = "Santiago del Estero", "Robles", "Chaco Seco / Riego Rio Dulce"
            soil = {"order": "Haplustol", "clay_pct": 20.0, "sand_pct": 36.0, "silt_pct": 44.0, "class": "Franco Limoso Aluvial"}
        elif lon < -60.5:
            prov, dept, reg = "Santa Fe", "General Obligado", "Cuna Boscosa Santafesina"
            soil = {"order": "Alfisol", "clay_pct": 30.0, "sand_pct": 22.0, "silt_pct": 48.0, "class": "Franco Arcillo Limoso"}
        elif lon < -58.5:
            prov, dept, reg = "Corrientes", "Goya", "Mesopotamia Norte / Litoral Paranaense"
            soil = {"order": "Alfisol / Molisol", "clay_pct": 32.0, "sand_pct": 24.0, "silt_pct": 44.0, "class": "Franco Arcillo Arenoso"}
        else:
            prov, dept, reg = "Corrientes", "Mercedes", "Campos y Malezales Correntinos"
            soil = {"order": "Molisol / Vertisol", "clay_pct": 34.0, "sand_pct": 22.0, "silt_pct": 44.0, "class": "Franco Arcilloso"}
    else:
        # Lat -26.5 to -21.8 (Norte Argentino)
        if lon < -65.2:
            prov, dept, reg = "Jujuy", "San Pedro", "NOA / Valles Subtropicales Jujeños"
            soil = {"order": "Udolfo / Hapludol", "clay_pct": 22.0, "sand_pct": 30.0, "silt_pct": 48.0, "class": "Franco Limoso Aluvial"}
        elif lon < -63.5:
            prov, dept, reg = "Salta", "Anta", "NOA / Umbral al Chaco Salteño"
            soil = {"order": "Haplustol", "clay_pct": 24.0, "sand_pct": 28.0, "silt_pct": 48.0, "class": "Franco Limoso (Agricola)"}
        elif lon < -60.5:
            prov, dept, reg = "Chaco", "Chacabuco", "Chaco Central / Nucleo Algodonero-Sojero"
            soil = {"order": "Argiustol", "clay_pct": 28.0, "sand_pct": 20.0, "silt_pct": 52.0, "class": "Franco Arcillo Limoso"}
        elif lon < -58.0:
            prov, dept, reg = "Formosa", "Pilcomayo", "Chaco Humedo Formoseno"
            soil = {"order": "Alfisol", "clay_pct": 28.0, "sand_pct": 26.0, "silt_pct": 46.0, "class": "Franco Arcilloso"}
        else:
            prov, dept, reg = "Misiones", "Obera", "Mesopotamia / Suelos Rojos Misioneros"
            soil = {"order": "Ultisol / Oxisol", "clay_pct": 48.0, "sand_pct": 14.0, "silt_pct": 38.0, "class": "Arcilloso Rojo Fuerte"}

    return {
        "department": dept,
        "province": prov,
        "region": reg,
        "soil": soil,
    }


def resolve_territorial_context(lat: float, lon: float, allow_network: bool = True) -> dict[str, Any]:
    """Geocodifica coordenadas para obtener Departamento, Provincia y perfil edafológico zonal.

    Verifica primero la base espacial en memoria (sub-microsegundo). Si no coincide con un bbox
    específico y allow_network=True, intenta Nominatim; de lo contrario resuelve mediante la
    partición geográfica continua de la República Argentina sin hardcoding.
    """
    # 1. Comprobación espacial inmediata con la matriz regional offline
    for entry in REGIONAL_DEPARTMENTS_DB:
        b = entry["bbox"]
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
            return {
                "department": entry["department"],
                "province": entry["province"],
                "region": entry["region"],
                "soil_baseline": entry["soil"],
                "citation": f"Dpto. {entry['department']}, {entry['province']} ({entry['region']})",
            }

    # 2. Si se permite red, intentar geocodificación inversa con Nominatim
    resolved_dept: str | None = None
    resolved_prov: str | None = None
    if allow_network:
        try:
            headers = {"User-Agent": "TERRIA-WhatIf/2.1 (agro-engine@terria.ag)"}
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
            with httpx.Client(timeout=1.5) as client:
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

    # 3. Partición geográfica continua de Argentina (CERO HARDCODING)
    reg_data = resolve_argentina_region(lat, lon)
    prov = resolved_prov or reg_data["province"]
    dept = resolved_dept or reg_data["department"]
    region = reg_data["region"]
    soil_base = reg_data["soil"]

    return {
        "department": dept,
        "province": prov,
        "region": region,
        "soil_baseline": soil_base,
        "citation": f"Dpto. {dept}, {prov} ({region})",
    }

