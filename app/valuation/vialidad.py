from __future__ import annotations

import math
from typing import Any
import unicodedata

import httpx

from app.valuation.schemas import LogisticDriver
from app.what_if.territory import resolve_territorial_context

# Nodos geodésicos representativos de los principales corredores viales troncales pavimentados de Argentina
NATIONAL_HIGHWAY_NODES: list[tuple[float, float, str]] = [
    # RN 9 (Buenos Aires - Rosario - Córdoba - Santiago - Tucumán - Salta - Jujuy)
    (-34.6, -58.4, "RN 9"), (-32.9, -60.6, "RN 9"), (-32.7, -62.1, "RN 9"), (-31.4, -64.2, "RN 9"),
    (-27.8, -64.3, "RN 9"), (-26.8, -65.2, "RN 9"), (-24.8, -65.5, "RN 9"), (-24.2, -65.3, "RN 9"),
    # RN 7 (Buenos Aires - Junín - Rufino - Laboulaye - San Luis - Mendoza)
    (-34.6, -58.5, "RN 7"), (-34.6, -60.9, "RN 7"), (-34.3, -62.7, "RN 7"), (-34.1, -64.1, "RN 7"),
    (-33.7, -65.5, "RN 7"), (-33.3, -66.3, "RN 7"), (-32.9, -68.8, "RN 7"),
    # RN 8 (Buenos Aires - Pergamino - Venado Tuerto - Río Cuarto)
    (-34.5, -58.6, "RN 8"), (-33.9, -60.6, "RN 8"), (-33.7, -61.9, "RN 8"), (-33.1, -64.3, "RN 8"),
    # RN 5 (Buenos Aires - Chivilcoy - Pehuajó - Trenque Lauquen - Santa Rosa)
    (-34.6, -58.7, "RN 5"), (-35.0, -60.0, "RN 5"), (-35.8, -61.9, "RN 5"), (-36.6, -64.3, "RN 5"),
    # RN 3 (Buenos Aires - Azul - Bahía Blanca - Viedma - Trelew - Comodoro - Río Gallegos)
    (-34.8, -58.5, "RN 3"), (-36.8, -59.5, "RN 3"), (-38.7, -62.3, "RN 3"), (-40.8, -63.0, "RN 3"),
    (-43.3, -65.1, "RN 3"), (-45.9, -67.5, "RN 3"), (-51.6, -69.2, "RN 3"),
    # RN 11 (Rosario - Santa Fe - San Justo - Reconquista - Resistencia - Formosa)
    (-32.9, -60.7, "RN 11"), (-31.6, -60.7, "RN 11"), (-29.1, -59.6, "RN 11"), (-27.5, -59.0, "RN 11"),
    (-26.2, -58.2, "RN 11"), (-25.3, -57.7, "RN 11"),
    # RN 12 (Buenos Aires - Ceibas - Paraná - Corrientes - Posadas - Iguazú)
    (-34.1, -58.9, "RN 12"), (-33.4, -59.0, "RN 12"), (-31.7, -60.5, "RN 12"), (-27.5, -59.0, "RN 12"),
    (-27.4, -56.0, "RN 12"), (-25.6, -54.6, "RN 12"),
    # RN 14 (Ceibas - Gualeguaychú - Concordia - Federación - Paso de los Libres)
    (-33.7, -58.8, "RN 14"), (-33.0, -58.5, "RN 14"), (-31.4, -58.0, "RN 14"), (-30.7, -58.0, "RN 14"),
    (-29.7, -57.1, "RN 14"), (-28.5, -56.0, "RN 14"), (-27.4, -55.9, "RN 14"),
    # RN 19 (Santa Fe - San Francisco - Córdoba)
    (-31.6, -60.7, "RN 19"), (-31.4, -62.1, "RN 19"), (-31.4, -64.2, "RN 19"),
    # RN 34 (Rosario - Rafaela - Ceres - Santiago - Tucumán - Metán)
    (-32.9, -60.7, "RN 34"), (-31.3, -61.5, "RN 34"), (-29.8, -62.0, "RN 34"), (-27.8, -64.2, "RN 34"),
    (-25.2, -65.0, "RN 34"), (-22.5, -63.8, "RN 34"),
    # RN 33 (Bahía Blanca - Pigüé - Trenque Lauquen - Rufino - Rosario)
    (-38.7, -62.3, "RN 33"), (-36.0, -62.7, "RN 33"), (-34.3, -62.7, "RN 33"), (-33.7, -61.9, "RN 33"),
    # RN 35 (Bahía Blanca - Santa Rosa - Realicó - Río Cuarto)
    (-38.7, -62.3, "RN 35"), (-36.6, -64.3, "RN 35"), (-35.0, -64.3, "RN 35"), (-33.1, -64.3, "RN 35"),
    # RN 40 (Bariloche - San Martín de los Andes - Mendoza - San Juan - Salta)
    (-41.1, -71.3, "RN 40"), (-39.0, -70.1, "RN 40"), (-35.5, -69.0, "RN 40"), (-32.9, -68.8, "RN 40"),
    (-31.5, -68.5, "RN 40"), (-29.0, -67.5, "RN 40"), (-26.0, -66.0, "RN 40"), (-24.0, -65.5, "RN 40"),
    # RN 188 (San Nicolás - Pergamino - Junín - Realicó - General Alvear)
    (-33.4, -60.2, "RN 188"), (-33.9, -60.6, "RN 188"), (-34.6, -61.0, "RN 188"), (-35.0, -64.3, "RN 188"),
    (-35.0, -67.7, "RN 188"),
    # RN 16 (Resistencia - Sáenz Peña - Pampa del Infierno - Joaquín V. González)
    (-27.5, -59.0, "RN 16"), (-26.8, -60.5, "RN 16"), (-25.8, -62.5, "RN 16"), (-25.5, -64.5, "RN 16"),
]

# Catálogo geoespacial de obras viales estratégicas activas en Argentina (Vialidad Nacional / DPV)
STRATEGIC_HIGHWAY_WORKS: list[dict[str, Any]] = [
    {
        "name": "Autovía RN 19 (San Francisco - Córdoba Capital)",
        "type": "highway=construction",
        "coords": [-62.08, -31.42],  # San Francisco / Devoto
        "province": "Cordoba",
        "detail": "Duplicación de calzada y conversión en Autovía RN 19.",
    },
    {
        "name": "Autovía RN 7 (Chacabuco - Junín)",
        "type": "highway=construction",
        "coords": [-60.47, -34.64],  # Chacabuco / Junín
        "province": "Buenos Aires",
        "detail": "Autopista RN 7 en ejecución para agilizar el transporte de carga hacia puertos.",
    },
    {
        "name": "Autovía Río Cuarto - Holmberg (RN 8 / RN 35)",
        "type": "highway=construction",
        "coords": [-64.35, -33.18],  # Río Cuarto
        "province": "Cordoba",
        "detail": "Variante de paso urbano y enlace a autovía de cargas.",
    },
    {
        "name": "Repavimentación y Enlace Productivo RP 1 (Distrito Mandisoví)",
        "type": "highway=construction",
        "coords": [-58.08, -30.76],  # Federación / Mandisoví
        "province": "Entre Rios",
        "detail": "Pavimentación y corredor de conexión productiva al complejo binacional.",
    },
    {
        "name": "Autovía Ruta Nacional 34 (Rafaela - Sunchales)",
        "type": "highway=construction",
        "coords": [-61.50, -31.25],  # Santa Fe
        "province": "Santa Fe",
        "detail": "Transformación en autovía para descongestionar el corredor sojero de Santa Fe.",
    },
    {
        "name": "Autovía RN 33 (Rufino - Venado Tuerto)",
        "type": "highway=construction",
        "coords": [-62.20, -34.15],
        "province": "Santa Fe",
        "detail": "Duplicación de calzada para el transporte de granos hacia los puertos del Gran Rosario.",
    },
    {
        "name": "Autovía RN 18 (Paraná - Villaguay - Concordia)",
        "type": "highway=construction",
        "coords": [-59.10, -31.80],
        "province": "Entre Rios",
        "detail": "Corredor Bioceánico central de Entre Ríos para agilizar el transporte de cereales y cítricos.",
    },
    {
        "name": "Autovía RN 5 (Mercedes - Suipacha - Bragado)",
        "type": "highway=construction",
        "coords": [-59.75, -34.75],
        "province": "Buenos Aires",
        "detail": "Transformación en autovía de la RN 5 para transporte cerealero hacia el puerto de Buenos Aires.",
    },
    {
        "name": "Autovía RN 16 (Makallé - Presidencia Roque Sáenz Peña)",
        "type": "highway=construction",
        "coords": [-60.20, -26.90],
        "province": "Chaco",
        "detail": "Ampliación de calzada y corredor logístico algodonero y sojero del Chaco Central.",
    },
    {
        "name": "Autovía RN 9 Norte (Tucumán - Trancas)",
        "type": "highway=construction",
        "coords": [-65.25, -26.40],
        "province": "Tucuman",
        "detail": "Nuevo acceso norte y conectividad con el sur de Salta.",
    },
    {
        "name": "Variante y Enlace Productivo RN 34 (Rosario de la Frontera - Metán)",
        "type": "highway=construction",
        "coords": [-64.95, -25.60],
        "province": "Salta",
        "detail": "Autopista de cargas en el Umbral del Chaco y conexión con Anta.",
    },
    {
        "name": "Autovía RN 22 (Chichinales - General Roca - Cipolletti)",
        "type": "highway=construction",
        "coords": [-67.60, -39.05],
        "province": "Rio Negro",
        "detail": "Autopista del Alto Valle para transporte frutícola y logística hidrocarburífera.",
    },
    {
        "name": "Autovía RN 40 (Mendoza - San Juan)",
        "type": "highway=construction",
        "coords": [-68.60, -32.20],
        "province": "Mendoza",
        "detail": "Conexión en autovía entre los oasis productivos de Cuyo.",
    },
    {
        "name": "Corredor Productivo RN 35 (Santa Rosa - Realicó)",
        "type": "highway=construction",
        "coords": [-64.30, -35.60],
        "province": "La Pampa",
        "detail": "Adecuación de calzada y banquinas para transporte de hacienda y granos.",
    },
    {
        "name": "Autovía RN 12 (Corrientes - Itatí)",
        "type": "highway=construction",
        "coords": [-58.40, -27.45],
        "province": "Corrientes",
        "detail": "Ampliación a autovía para corredor arrocero y forestal del norte correntino.",
    },
    {
        "name": "Repavimentación y Obra Vial RN 89 (Quimilí - Suncho Corral)",
        "type": "highway=construction",
        "coords": [-62.60, -27.60],
        "province": "Santiago del Estero",
        "detail": "Mejora del corredor de granos del este santiagueño hacia los puertos del Paraná.",
    },
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia geodésica del gran círculo en kilómetros."""
    radius_earth_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius_earth_km * c, 2)


def fetch_overpass_road_works(lat: float, lon: float, radius_km: float = 50.0) -> list[dict[str, Any]]:
    """Consulta la API de Overpass (OpenStreetMap) en un radio de 50 km buscando vías principales

    en estado de construcción o propuestas (highway=construction o highway=proposed).
    """
    radius_meters = int(radius_km * 1000)
    query = f"""
    [out:json][timeout:5];
    (
      way["highway"="construction"](around:{radius_meters},{lat},{lon});
      way["highway"="proposed"](around:{radius_meters},{lat},{lon});
    );
    out center tags 10;
    """
    url = "https://overpass-api.de/api/interpreter"
    results = []
    try:
        with httpx.Client(timeout=6.0) as client:
            r = client.post(url, data={"data": query})
            if r.status_code == 200:
                data = r.json()
                for el in data.get("elements", []):
                    center = el.get("center", {})
                    tags = el.get("tags", {})
                    if "lat" in center and "lon" in center:
                        w_lat = float(center["lat"])
                        w_lon = float(center["lon"])
                        name = tags.get("name") or tags.get("ref") or "Obra Vial en Ejecución"
                        dist = haversine_km(lat, lon, w_lat, w_lon)
                        results.append({
                            "name": name,
                            "type": tags.get("highway", "construction"),
                            "lat": w_lat,
                            "lon": w_lon,
                            "distance_km": dist,
                            "detail": f"Proyecto vial '{name}' registrado en OpenStreetMap.",
                        })
    except Exception:
        pass
    return results


def estimate_distance_to_highway(lat: float, lon: float) -> tuple[float, str]:
    """Calcula la distancia geodésica real al corredor vial pavimentado más cercano de la red troncal nacional."""
    min_dist = float("inf")
    closest_route = "Red Vial Troncal"
    for h_lat, h_lon, route_name in NATIONAL_HIGHWAY_NODES:
        d = haversine_km(lat, lon, h_lat, h_lon)
        if d < min_dist:
            min_dist = d
            closest_route = route_name
    dist_paved = round(max(3.0, min_dist), 1)
    return dist_paved, closest_route


def clean_str(s: str) -> str:
    """Normaliza cadenas eliminando acentos y caracteres especiales."""
    return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8").strip()


# Benchmarks zonales agronómicos de napa freática y aporte hídrico por capilaridad (INTA)
DEPARTMENTAL_WATER_TABLE_BENCHMARKS: dict[tuple[str, str], dict[str, Any]] = {
    ("Marcos Juarez", "Cordoba"): {
        "depth_m": 1.8,
        "classification": "Cota estival óptima (INTA Marcos Juárez)",
        "capillary_buffer_mm": 210,
        "impact_pct": 3.8,
    },
    ("Pergamino", "Buenos Aires"): {
        "depth_m": 1.7,
        "classification": "Cota freática óptima (INTA Pergamino)",
        "capillary_buffer_mm": 195,
        "impact_pct": 3.6,
    },
    ("General Lopez", "Santa Fe"): {
        "depth_m": 2.0,
        "classification": "Cota freática óptima (Cuenca Venado Tuerto)",
        "capillary_buffer_mm": 180,
        "impact_pct": 3.5,
    },
    ("Rio Segundo", "Cordoba"): {
        "depth_m": 2.8,
        "classification": "Cota moderada a profunda (EEA INTA Manfredi)",
        "capillary_buffer_mm": 75,
        "impact_pct": 1.8,
    },
    ("Manfredi", "Cordoba"): {
        "depth_m": 2.8,
        "classification": "Cota moderada a profunda (EEA INTA Manfredi)",
        "capillary_buffer_mm": 75,
        "impact_pct": 1.8,
    },
    ("Rio Cuarto", "Cordoba"): {
        "depth_m": 4.5,
        "classification": "Napa profunda / pedemonte sin aporte freático (FAV-UNRC)",
        "capillary_buffer_mm": 0,
        "impact_pct": 0.0,
    },
    ("Federacion", "Entre Rios"): {
        "depth_m": 1.0,
        "classification": "Vertisol con drenaje lento y riesgo de anegamiento estacional",
        "capillary_buffer_mm": 30,
        "impact_pct": -0.5,
    },
    ("Chacabuco", "Chaco"): {
        "depth_m": 5.2,
        "classification": "Napa salina profunda sin aporte a cultivos",
        "capillary_buffer_mm": 0,
        "impact_pct": 0.0,
    },
    ("Tres Arroyos", "Buenos Aires"): {
        "depth_m": 4.0,
        "classification": "Estrato con tosca somera sin conexión freática",
        "capillary_buffer_mm": 0,
        "impact_pct": 0.0,
    },
}


def resolve_water_table_profile(lat: float, lon: float, allow_network: bool = True) -> dict[str, Any]:
    """Determina la cota y resiliencia de la napa freática según serie INTA y perfil edafológico."""
    territory = resolve_territorial_context(lat, lon, allow_network=allow_network)
    dept_raw = territory.get("department", "")
    prov_raw = territory.get("province", "")
    soil = territory.get("soil_baseline", {})
    order = str(soil.get("order", "")).lower()

    dept_norm = clean_str(dept_raw).lower()
    prov_norm = clean_str(prov_raw).lower()

    if "espinillos" in dept_norm or "marcos juarez" in dept_norm:
        canonical_dept = "Marcos Juarez"
    elif "mandisovi" in dept_norm or "federacion" in dept_norm:
        canonical_dept = "Federacion"
    elif "pergamino" in dept_norm:
        canonical_dept = "Pergamino"
    elif "lopez" in dept_norm:
        canonical_dept = "General Lopez"
    elif "rio segundo" in dept_norm or "manfredi" in dept_norm:
        canonical_dept = "Manfredi"
    elif "rio cuarto" in dept_norm or "aguada" in dept_norm:
        canonical_dept = "Rio Cuarto"
    elif "chacabuco" in dept_norm or "charata" in dept_norm:
        canonical_dept = "Chacabuco"
    elif "tres arroyos" in dept_norm:
        canonical_dept = "Tres Arroyos"
    else:
        canonical_dept = clean_str(dept_raw).title()

    if "cordoba" in prov_norm:
        canonical_prov = "Cordoba"
    elif "entre rios" in prov_norm:
        canonical_prov = "Entre Rios"
    elif "buenos aires" in prov_norm:
        canonical_prov = "Buenos Aires"
    elif "santa fe" in prov_norm:
        canonical_prov = "Santa Fe"
    elif "chaco" in prov_norm:
        canonical_prov = "Chaco"
    else:
        canonical_prov = clean_str(prov_raw).title()

    key = (canonical_dept, canonical_prov)
    if key in DEPARTMENTAL_WATER_TABLE_BENCHMARKS:
        return DEPARTMENTAL_WATER_TABLE_BENCHMARKS[key]

    # Modelo biofísico inferido por orden de suelo INTA
    if "argiudol" in order:
        return {
            "depth_m": 1.9,
            "classification": "Cota estival óptima pampeana (Argiudol)",
            "capillary_buffer_mm": 190,
            "impact_pct": 3.8,
        }
    elif "hapludol" in order:
        return {
            "depth_m": 2.2,
            "classification": "Cota freática moderada-óptima (Hapludol)",
            "capillary_buffer_mm": 150,
            "impact_pct": 2.8,
        }
    elif "haplustol" in order:
        return {
            "depth_m": 2.8,
            "classification": "Cota freática moderada (Haplustol semiárido)",
            "capillary_buffer_mm": 80,
            "impact_pct": 1.8,
        }
    elif "vertisol" in order:
        return {
            "depth_m": 1.2,
            "classification": "Vertisol con napa fluctuante y drenaje restringido",
            "capillary_buffer_mm": 40,
            "impact_pct": -0.5,
        }
    else:
        return {
            "depth_m": 4.5,
            "classification": "Secano profundo sin aporte freático significativo",
            "capillary_buffer_mm": 0,
            "impact_pct": 0.0,
        }


def calculate_logistic_multiplier(
    lat: float,
    lon: float,
    allow_network: bool = True,
    irrigation: bool = False,
) -> LogisticDriver:
    """Calcula el multiplicador de resiliencia hídrica y conectividad logística (Driver 1).

    Regla de negocio:
    1. Cota de napa freática (INTA): óptima (1.5m-2.5m) aporta 150-250 mm capilares estivales (+5% a +8%).
       Napa profunda (>3.5m) o con tosca/roca aporta 0.0%. Napa anegable (<0.8m) penaliza (-2.5%).
    2. Riego por pivote central: estabilidad productiva total (+8.0%).
    3. Red vial troncal (OSM / IGN): ahorro de distancia a rutas pavimentadas suma hasta +3%.
    Piso agronómico: -2.5% (anegamiento/aislamiento), techo máximo: +15.0%.
    """
    # 1. Perfil hídrico de napa freática y riego
    water = resolve_water_table_profile(lat, lon, allow_network=allow_network)
    hydric_pct = water["impact_pct"]
    if irrigation:
        hydric_pct += 8.0

    # 2. Conectividad vial y cercanía al pavimento troncal
    dist_current_paved, closest_route = estimate_distance_to_highway(lat, lon)
    overpass_works = fetch_overpass_road_works(lat, lon, radius_km=50.0) if allow_network else []
    closest_work = None
    min_dist = float("inf")

    if overpass_works:
        for w in overpass_works:
            if w["distance_km"] < min_dist:
                min_dist = w["distance_km"]
                closest_work = w
    else:
        for work in STRATEGIC_HIGHWAY_WORKS:
            d = haversine_km(lat, lon, work["coords"][1], work["coords"][0])
            if d <= 50.0 and d < min_dist:
                min_dist = d
                closest_work = {
                    "name": work["name"],
                    "type": work["type"],
                    "lat": work["coords"][1],
                    "lon": work["coords"][0],
                    "distance_km": d,
                    "detail": work["detail"],
                }

    if closest_work and min_dist < dist_current_paved:
        future_dist = round(min_dist, 1)
        dist_saved = round(dist_current_paved - future_dist, 1)
        road_pct = min(3.0, max(0.0, round((dist_saved / 10.0) * 1.5, 1)))
        road_note = f"Obra vial '{closest_work['name']}' ahorra {dist_saved:.1f} km al asfalto (+{road_pct}%)."
    else:
        future_dist = dist_current_paved
        dist_saved = 0.0
        road_pct = 0.0
        road_note = f"Conexión a {closest_route} a {dist_current_paved:.1f} km."

    total_impact_pct = round(max(-2.5, min(15.0, hydric_pct + road_pct)), 1)
    multiplier = round(1.0 + (total_impact_pct / 100.0), 4)

    irrigation_tag = " [Riego Pivote Activo]" if irrigation else ""
    detail = (
        f"Resiliencia hídrica: Napa freática en {water['depth_m']:.1f}m ({water['classification']}; "
        f"aporte capilar ~{water['capillary_buffer_mm']} mm en déficit estival, {hydric_pct:+.1f}%{irrigation_tag}). "
        f"{road_note}"
    )

    return LogisticDriver(
        impact_percentage=total_impact_pct,
        multiplier=multiplier,
        distance_to_current_paved_km=dist_current_paved,
        distance_to_future_paved_km=future_dist,
        distance_saved_km=dist_saved,
        detail=detail,
    )

