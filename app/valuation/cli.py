from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any
from uuid import UUID

from app.store import get_field_store
from app.valuation.agronomic_trend import calculate_agronomic_multiplier
from app.valuation.idecor import fetch_base_land_value
from app.valuation.vialidad import calculate_logistic_multiplier
from app.valuation.engine import run_land_valuation_projection
from app.what_if.geometry import parse_geometry_input

# Paleta de estilos ANSI
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


class Style:
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    ITALIC = "\033[3m" if USE_COLOR else ""

    # Colores
    CYAN = "\033[36m" if USE_COLOR else ""
    GREEN = "\033[32m" if USE_COLOR else ""
    YELLOW = "\033[33m" if USE_COLOR else ""
    BLUE = "\033[34m" if USE_COLOR else ""
    MAGENTA = "\033[35m" if USE_COLOR else ""
    WHITE = "\033[37m" if USE_COLOR else ""
    BRIGHT_GREEN = "\033[92m" if USE_COLOR else ""
    BRIGHT_CYAN = "\033[96m" if USE_COLOR else ""
    BRIGHT_YELLOW = "\033[93m" if USE_COLOR else ""
    BRIGHT_WHITE = "\033[97m" if USE_COLOR else ""
    GRAY = "\033[90m" if USE_COLOR else ""


PRESETS: dict[str, dict[str, Any]] = {
    "marcos_juarez": {
        "name": "Lote Marcos Juárez (Zona Núcleo - Córdoba)",
        "department": "Marcos Juárez",
        "province": "Córdoba",
        "lat": -32.70,
        "lon": -62.10,
        "ha": 500.0,
        "description": "Suelo Argiudol Clase I, alta aptitud agrícola núcleo pampeana.",
    },
    "pergamino": {
        "name": "Lote Pergamino (Pampa Húmeda - Buenos Aires)",
        "department": "Pergamino",
        "province": "Buenos Aires",
        "lat": -33.89,
        "lon": -60.57,
        "ha": 420.0,
        "description": "Zona núcleo maicera y sojera tradicional bonaerense.",
    },
    "venado_tuerto": {
        "name": "Lote Venado Tuerto (Zona Núcleo Sur - Santa Fe)",
        "department": "General López",
        "province": "Santa Fe",
        "lat": -33.74,
        "lon": -61.96,
        "ha": 650.0,
        "description": "Suelo Hapludol / Argiudol de máxima productividad maicera.",
    },
    "federacion": {
        "name": "Lote Federación Mandisoví (Mesopotamia - Entre Ríos)",
        "department": "Federación",
        "province": "Entre Ríos",
        "lat": -30.98,
        "lon": -57.92,
        "ha": 280.0,
        "description": "Suelo Vertisol peludal con plusvalía por obras viales RP 1.",
    },
    "charata": {
        "name": "Lote Charata (Chaco Central / Región Chaqueña)",
        "department": "Chacabuco",
        "province": "Chaco",
        "lat": -27.21,
        "lon": -61.19,
        "ha": 1200.0,
        "description": "Frontera agrícola de alta escala en soja, maíz y algodón.",
    },
    "tres_arroyos": {
        "name": "Lote Tres Arroyos (Pampa Austral / Fina - Buenos Aires)",
        "department": "Tres Arroyos",
        "province": "Buenos Aires",
        "lat": -38.37,
        "lon": -60.27,
        "ha": 800.0,
        "description": "Cuenca triguera y cebadera del sur bonaerense con tosca somera.",
    },
}

SUGGESTED_REGIONS = [
    ("Marcos Juárez / Leones", "Córdoba - Zona Núcleo Pampeana", -32.70, -62.10, 500.0),
    ("Pergamino / Rojas", "Buenos Aires - Pampa Húmeda Ondulada", -33.89, -60.57, 420.0),
    ("Venado Tuerto / Casilda", "Santa Fe - Zona Núcleo Sur Maicera", -33.74, -61.96, 650.0),
    ("Río Cuarto / Sampacho", "Córdoba - Pampa Arenosa", -33.13, -64.35, 450.0),
    ("Federación / Chajarí", "Entre Ríos - Mesopotamia / Vertisoles", -30.98, -57.92, 280.0),
    ("Charata / Las Breñas", "Chaco - Región Chaqueña Central", -27.21, -61.19, 1200.0),
    ("Tres Arroyos / Necochea", "Buenos Aires - Pampa Austral / Fina", -38.37, -60.27, 800.0),
    ("Quimilí / Suncho Corral", "Santiago del Estero - Secano Agrícola", -27.64, -62.41, 950.0),
    ("Anta / Joaquín V. González", "Salta - NOA / Umbral al Chaco", -25.08, -64.18, 1500.0),
]


def _box_from_centroid(lat: float, lon: float, ha: float) -> list[list[float]]:
    side_meters = math.sqrt(ha * 10000.0)
    d_lat = (side_meters / 111320.0) / 2.0
    d_lon = (side_meters / (111320.0 * math.cos(math.radians(lat)))) / 2.0
    return [
        [round(lon - d_lon, 6), round(lat - d_lat, 6)],
        [round(lon + d_lon, 6), round(lat - d_lat, 6)],
        [round(lon + d_lon, 6), round(lat + d_lat, 6)],
        [round(lon - d_lon, 6), round(lat + d_lat, 6)],
        [round(lon - d_lon, 6), round(lat - d_lat, 6)],
    ]


def _render_bar(pct: float, max_pct: float = 20.0, length: int = 18) -> str:
    """Genera una barra visual de progreso ASCII con porcentaje."""
    filled_len = int(round(length * min(1.0, max(0.0, pct / max_pct))))
    empty_len = length - filled_len
    bar = f"{Style.BRIGHT_GREEN}{'█' * filled_len}{Style.GRAY}{'░' * empty_len}{Style.RESET}"
    return f"[{bar}] {Style.BOLD}{pct:+.1f}%{Style.RESET}"


def _fmt_usd(val: float) -> str:
    """Formatea moneda en dólares estadounidenses."""
    return f"USD {val:,.2f}"


def render_single_valuation(res: Any, include_audit: bool = True) -> None:
    """Renderiza la proyección de valor de un lote con formato visual estructurado y de alta legibilidad."""
    v = res.valuation
    S = Style

    # Encabezado
    title = f" PROYECCIÓN DE VALOR DE TIERRA A {v.projection_years} AÑOS: {res.lot_name.upper()} "
    width = 82
    print(f"\n{S.BRIGHT_CYAN}╔{'═' * (width - 2)}╗{S.RESET}")
    print(f"{S.BRIGHT_CYAN}║{S.BOLD}{S.BRIGHT_WHITE}{title.center(width - 2)}{S.RESET}{S.BRIGHT_CYAN}║{S.RESET}")
    print(f"{S.BRIGHT_CYAN}╠{'═' * (width - 2)}╣{S.RESET}")
    subtitle = "Módulo FinTech & Real Estate Agropecuario · TERRIA Engine v3.0"
    print(f"{S.BRIGHT_CYAN}║{S.DIM}{subtitle.center(width - 2)}{S.RESET}{S.BRIGHT_CYAN}║{S.RESET}")
    print(f"{S.BRIGHT_CYAN}╚{'═' * (width - 2)}╝{S.RESET}\n")

    # 1. Tarjeta de Resumen Ejecutivo
    cagr_eff = ((v.projected_value_usd_ha / v.base_value_usd_ha) ** (1.0 / v.projection_years) - 1.0) * 100.0

    print(f"{S.BRIGHT_YELLOW}┌─ 📌 RESUMEN EJECUTIVO & APRECIACIÓN DEL ACTIVO {'─' * (width - 48)}┐{S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Superficie Evaluada:{S.RESET}   {v.financial_totals.surface_ha:.2f} hectáreas")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Horizonte Temporal:{S.RESET}    {v.current_year} ➔ {v.target_year} ({v.projection_years} años de proyección)")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Valor Base Actual (T0):{S.RESET}    {S.BRIGHT_WHITE}{_fmt_usd(v.base_value_usd_ha)} / ha{S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Valor Proyectado (T{v.projection_years}):{S.RESET}   {S.BRIGHT_GREEN}{_fmt_usd(v.projected_value_usd_ha)} / ha{S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Apreciación Total:{S.RESET}         {S.BRIGHT_GREEN}{S.BOLD}+{v.total_appreciation_percentage:.1f}% (ROI Pasivo Total){S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Tasa Anual Efectiva:{S.RESET}       {S.BRIGHT_CYAN}{S.BOLD}+{cagr_eff:.2f}% / año (CAGR Compuesto){S.RESET}")
    print(f"{S.BRIGHT_YELLOW}│{S.RESET}  {S.BOLD}Ganancia de Capital Total:{S.RESET} {S.BRIGHT_GREEN}{S.BOLD}{_fmt_usd(v.financial_totals.total_capital_gain_usd)}{S.RESET} {S.DIM}(Para todo el lote){S.RESET}")
    print(f"{S.BRIGHT_YELLOW}└{'─' * (width - 2)}┘{S.RESET}\n")

    # 2. Desglose de los 3 Drivers
    log = v.drivers_breakdown.logistic_improvement
    agro = v.drivers_breakdown.agronomic_trend
    mkt = v.drivers_breakdown.market_appreciation

    print(f"{S.BRIGHT_CYAN}┌─ ⚙️  DESGLOSE DE LOS 3 MOTORES DE VALOR (DRIVERS) {'─' * (width - 50)}┐{S.RESET}")

    # Driver 1: Vial
    print(f"{S.BRIGHT_CYAN}│{S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}  {S.BOLD}1. 🛣️  INFRAESTRUCTURA VIAL & LOGÍSTICA{S.RESET}  {S.DIM}(M_log = {log.multiplier:.4f}x){S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     Impacto: {_render_bar(log.impact_percentage, 15.0)}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • Distancia actual al asfalto:      {log.distance_to_current_paved_km:.1f} km")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • Distancia con nueva traza vial:   {log.distance_to_future_paved_km:.1f} km {S.BRIGHT_GREEN}(Ahorro: {log.distance_saved_km:.1f} km){S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • {S.DIM}Detalle:{S.RESET} {log.detail}")

    # Driver 2: Agronómico
    print(f"{S.BRIGHT_CYAN}│{S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}  {S.BOLD}2. 🌾 PRODUCTIVIDAD AGRONÓMICA & GENÉTICA (SAGyP 15 AÑOS){S.RESET}  {S.DIM}(M_agro = {agro.multiplier:.4f}x){S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     Impacto: {_render_bar(agro.impact_percentage, 15.0)}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • CAGR histórico departamental:     {S.BRIGHT_CYAN}+{agro.cagr_annual_pct:.2f}% / año{S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • Factor de traslado al suelo:      0.80 (80% del rinde capitaliza en tierra)")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • {S.DIM}Detalle:{S.RESET} {agro.detail}")

    # Driver 3: Mercado
    print(f"{S.BRIGHT_CYAN}│{S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}  {S.BOLD}3. 📈 MERCADO INMOBILIARIO RURAL (REFUGIO EN USD){S.RESET}  {S.DIM}(M_mkt = {mkt.multiplier:.4f}x){S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     Impacto: {_render_bar(mkt.impact_percentage, 20.0)}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • Tasa macro de apreciación base:   {S.BRIGHT_CYAN}+{mkt.annual_rate_pct:.2f}% / año compuesto{S.RESET}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}     • {S.DIM}Detalle:{S.RESET} {mkt.detail}")
    print(f"{S.BRIGHT_CYAN}│{S.RESET}")
    print(f"{S.BRIGHT_CYAN}└{'─' * (width - 2)}┘{S.RESET}\n")

    # 3. Ecuación Matemática Integral
    print(f"{S.WHITE}┌─ 📐 ECUACIÓN INTEGRAL DE VALUACIÓN {'─' * (width - 36)}┐{S.RESET}")
    print(f"{S.WHITE}│{S.RESET}  Fórmula:  {S.BOLD}Valor_Proyectado = V0 × M_log × M_agro × M_mkt{S.RESET}")
    print(
        f"{S.WHITE}│{S.RESET}  Cálculo:  {S.BRIGHT_GREEN}{_fmt_usd(v.projected_value_usd_ha)}{S.RESET} = "
        f"{_fmt_usd(v.base_value_usd_ha)} × {log.multiplier:.4f} × {agro.multiplier:.4f} × {mkt.multiplier:.4f}"
    )
    print(f"{S.WHITE}└{'─' * (width - 2)}┘{S.RESET}\n")

    # 4. Totales Financieros del Lote
    fin = v.financial_totals
    print(f"{S.BRIGHT_GREEN}┌─ 💼 TOTALES FINANCIEROS DEL LOTE COMPLETO ({fin.surface_ha:.1f} ha) {'─' * (width - 53)}┐{S.RESET}")
    print(f"{S.BRIGHT_GREEN}│{S.RESET}  Valor Total del Lote Hoy ({v.current_year}):        {S.BOLD}{_fmt_usd(fin.total_base_value_usd)}{S.RESET}")
    print(f"{S.BRIGHT_GREEN}│{S.RESET}  Valor Total del Lote a {v.target_year} ({v.projection_years}a):       {S.BOLD}{_fmt_usd(fin.total_projected_value_usd)}{S.RESET}")
    print(f"{S.BRIGHT_GREEN}│{S.RESET}  ────────────────────────────────────────────────────────────────────────")
    print(f"{S.BRIGHT_GREEN}│{S.RESET}  {S.BOLD}GANANCIA DE CAPITAL NETA ESTIMADA:{S.RESET}      {S.BRIGHT_GREEN}{S.BOLD}+{_fmt_usd(fin.total_capital_gain_usd)}{S.RESET}")
    print(f"{S.BRIGHT_GREEN}└{'─' * (width - 2)}┘{S.RESET}\n")

    # 5. Certificación On-Chain & Auditoría
    print(f"{S.MAGENTA}┌─ 🔐 CERTIFICACIÓN CRIPTOGRÁFICA ON-CHAIN (SOLANA MEMO READY) {'─' * (width - 61)}┐{S.RESET}")
    print(f"{S.MAGENTA}│{S.RESET}  {S.BOLD}SHA-256 Content Hash:{S.RESET} {S.CYAN}{v.content_hash}{S.RESET}")
    if include_audit and v.audit_urls:
        print(f"{S.MAGENTA}│{S.RESET}")
        print(f"{S.MAGENTA}│{S.RESET}  {S.BOLD}Fuentes Públicas de Auditoría Georreferenciada:{S.RESET}")
        for k, u in v.audit_urls.items():
            name_label = k.replace("_", " ").title()
            print(f"{S.MAGENTA}│{S.RESET}   • {S.BOLD}{name_label}:{S.RESET} {S.DIM}{u}{S.RESET}")
    print(f"{S.MAGENTA}└{'─' * (width - 2)}┘{S.RESET}\n")


def compare_all_presets(years: int = 5, allow_network: bool = True) -> None:
    """Ejecuta la proyección comparativa entre todas las regiones agropecuarias argentinas."""
    S = Style
    print(f"\n{S.BRIGHT_CYAN}╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗{S.RESET}")
    print(f"{S.BRIGHT_CYAN}║{S.BOLD}{S.BRIGHT_WHITE}         📊 TABLA COMPARATIVA REGIONAL: PROYECCIÓN DE VALOR DE TIERRA A {years} AÑOS (TODOS LOS PRESETS)        {S.RESET}{S.BRIGHT_CYAN}║{S.RESET}")
    print(f"{S.BRIGHT_CYAN}╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝{S.RESET}\n")

    rows = []
    for key, p in PRESETS.items():
        geom = _box_from_centroid(p["lat"], p["lon"], p["ha"])
        res = run_land_valuation_projection(
            geometry_data=geom,
            lot_name=p["name"],
            projection_years=years,
            include_audit=False,
            allow_network=allow_network,
        )
        v = res.valuation
        rows.append({
            "key": key,
            "region": f"{p['department']} ({p['province'][:4]}.)",
            "ha": f"{p['ha']:.0f} ha",
            "base_ha": f"${v.base_value_usd_ha:,.0f}",
            "proj_ha": f"${v.projected_value_usd_ha:,.0f}",
            "m_log": f"{v.drivers_breakdown.logistic_improvement.multiplier:.3f}x",
            "m_agro": f"{v.drivers_breakdown.agronomic_trend.multiplier:.3f}x",
            "m_mkt": f"{v.drivers_breakdown.market_appreciation.multiplier:.3f}x",
            "roi": f"+{v.total_appreciation_percentage:.1f}%",
            "gain_total": f"${v.financial_totals.total_capital_gain_usd / 1000:,.1f}k",
        })

    cols = [
        ("Zona / Departamento", 24, "<"),
        ("Sup (ha)", 10, ">"),
        ("Base USD/ha", 12, ">"),
        ("Proy USD/ha", 12, ">"),
        ("M_log", 8, ">"),
        ("M_agro", 8, ">"),
        ("M_mkt", 8, ">"),
        ("ROI %", 9, ">"),
        ("Ganancia Lote", 15, ">"),
    ]

    top_border = "┌─" + "─┬─".join("─" * w for _, w, _ in cols) + "─┐"
    mid_border = "├─" + "─┼─".join("─" * w for _, w, _ in cols) + "─┤"
    bot_border = "└─" + "─┴─".join("─" * w for _, w, _ in cols) + "─┘"

    header_cells = [f"{title:{align}{w}}" for title, w, align in cols]
    header_line = "│ " + " │ ".join(header_cells) + " │"

    print(f"{S.BOLD}{top_border}{S.RESET}")
    print(f"{S.BOLD}{header_line}{S.RESET}")
    print(f"{S.BOLD}{mid_border}{S.RESET}")

    for r in rows:
        c1 = f"{r['region']:<24}"
        c2 = f"{r['ha']:>10}"
        c3 = f"{r['base_ha']:>12}"
        c4 = f"{S.BRIGHT_GREEN}{r['proj_ha']:>12}{S.RESET}"
        c5 = f"{r['m_log']:>8}"
        c6 = f"{r['m_agro']:>8}"
        c7 = f"{r['m_mkt']:>8}"
        c8 = f"{S.BRIGHT_CYAN}{S.BOLD}{r['roi']:>9}{S.RESET}"
        c9 = f"{S.BRIGHT_GREEN}{r['gain_total']:>15}{S.RESET}"
        row_str = f"│ {c1} │ {c2} │ {c3} │ {c4} │ {c5} │ {c6} │ {c7} │ {c8} │ {c9} │"
        print(row_str)

    print(f"{S.BOLD}{bot_border}{S.RESET}")
    print(f"\n{S.DIM}* Nota: M_log = Multiplicador Logístico Vial, M_agro = Tendencia Agronómica SAGyP, M_mkt = Inflación Mercado USD.{S.RESET}\n")


def run_interactive_wizard() -> None:
    """Asistente interactivo guiado por consola para ingresar datos de lote y ver el flujo en tiempo real."""
    S = Style

    width = 82
    print(f"\n{S.BRIGHT_GREEN}╔{'═' * (width - 2)}╗{S.RESET}")
    print(f"{S.BRIGHT_GREEN}║{S.BOLD}{S.BRIGHT_WHITE}{'🌱 ASISTENTE INTERACTIVO: VALUACIÓN DE CAMPO A FUTURO'.center(width - 2)}{S.RESET}{S.BRIGHT_GREEN}║{S.RESET}")
    print(f"{S.BRIGHT_GREEN}╠{'═' * (width - 2)}╣{S.RESET}")
    print(f"{S.BRIGHT_GREEN}║{S.DIM}{'TERRIA FinTech & Real Estate · Simulación Guiada Paso a Paso'.center(width - 2)}{S.RESET}{S.BRIGHT_GREEN}║{S.RESET}")
    print(f"{S.BRIGHT_GREEN}╚{'═' * (width - 2)}╝{S.RESET}\n")

    while True:
        # Paso 1: Nombre
        print(f"{S.BOLD}{S.BRIGHT_CYAN}[Paso 1 de 5]{S.RESET} {S.BOLD}Identificación del Campo:{S.RESET}")
        default_name = "Estancia La Juanita"
        lot_name_in = input(f"  > Nombre del lote/campo [{default_name}]: ").strip()
        lot_name = lot_name_in if lot_name_in else default_name

        # Paso 2: Ubicación
        print(f"\n{S.BOLD}{S.BRIGHT_CYAN}[Paso 2 de 5]{S.RESET} {S.BOLD}Definición Geográfica del Campo:{S.RESET}")
        print("  ¿Cómo deseas ingresar la ubicación del lote?")
        print(f"    {S.BRIGHT_YELLOW}1){S.RESET} Pegar polígono en formato GeoJSON (JSON directo o ruta a archivo .json / .geojson)")
        print(f"    {S.BRIGHT_YELLOW}2){S.RESET} Ingresar coordenadas geográficas exactas (Latitud y Longitud)")
        print(f"    {S.BRIGHT_YELLOW}3){S.RESET} Seleccionar un campo ya persistido en la base de datos de TERRIA")

        mode_choice = input("  > Selecciona opción (1, 2 o 3) [1]: ").strip() or "1"

        lat = -32.70
        lon = -62.10
        field_uuid = None
        geom_data = None
        default_ha = 350.0

        if mode_choice == "1":
            print(f"\n  {S.DIM}Ingresa el polígono GeoJSON (o la ruta a un archivo .geojson / .json):{S.RESET}")
            print(f"  {S.GRAY}Ejemplo: {{\"type\": \"Polygon\", \"coordinates\": [[[-62.11, -32.70], [-62.09, -32.70], [-62.09, -32.69], [-62.11, -32.69], [-62.11, -32.70]]]}}{S.RESET}")
            geo_raw = input("  > GeoJSON o ruta [Enter para polígono Marcos Juárez por defecto]: ").strip()

            if geo_raw:
                if os.path.exists(geo_raw):
                    try:
                        with open(geo_raw, "r", encoding="utf-8") as f:
                            geom_data = json.load(f)
                        print(f"  {S.BRIGHT_GREEN}✓ Archivo '{geo_raw}' cargado exitosamente.{S.RESET}")
                    except Exception as e:
                        print(f"  {S.YELLOW}Error al leer archivo GeoJSON: {e}.{S.RESET}")
                else:
                    try:
                        geom_data = json.loads(geo_raw)
                    except Exception as e:
                        print(f"  {S.YELLOW}Error al parsear GeoJSON: {e}. Usando polígono por defecto.{S.RESET}")

            if geom_data is None:
                # Default Marcos Juárez GeoJSON
                geom_data = {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-62.11, -32.70],
                            [-62.09, -32.70],
                            [-62.09, -32.69],
                            [-62.11, -32.69],
                            [-62.11, -32.70],
                        ]
                    ],
                }

            try:
                c_lat, c_lon, calc_ha, _ = parse_geometry_input(geom_data)
                lat, lon = c_lat, c_lon
                default_ha = calc_ha if calc_ha > 0 else 350.0
                print(f"  {S.BRIGHT_GREEN}✓ Geometría procesada exitosamente:{S.RESET}")
                print(f"    • Centroide calculado: Lat {c_lat:.5f}, Lon {c_lon:.5f}")
                print(f"    • Superficie calculada por Shoelace: {calc_ha:.2f} ha")
            except Exception as e:
                print(f"  {S.YELLOW}Aviso al calcular métricas de geometría: {e}.{S.RESET}")

        elif mode_choice == "2":
            print(f"\n  {S.DIM}Ingresa las coordenadas en formato decimal (ej: Lat -33.89, Lon -60.57):{S.RESET}")
            lat_str = input("  > Latitud [-32.70]: ").strip()
            lon_str = input("  > Longitud [-62.10]: ").strip()
            try:
                lat = float(lat_str) if lat_str else -32.70
                lon = float(lon_str) if lon_str else -62.10
            except ValueError:
                print(f"  {S.YELLOW}Coordenadas inválidas. Usando Marcos Juárez por defecto.{S.RESET}")
                lat, lon = -32.70, -62.10
        elif mode_choice == "3":
            store = get_field_store()
            fields = store.list()
            if fields:
                print(f"\n  {S.BOLD}Campos reales autoritativos en la base de datos de TERRIA:{S.RESET}")
                for idx, f in enumerate(fields, start=1):
                    loc = f"{f.locality}, {f.province}" if f.locality and f.province else (f.province or "Argentina")
                    print(f"    {S.BRIGHT_GREEN}★ [{idx}]{S.RESET} {S.BOLD}{f.name}{S.RESET} ({loc}) — {S.BRIGHT_YELLOW}{f.area_hectares:.2f} ha{S.RESET}")
                f_idx_str = input(f"  > Selecciona número [1-{len(fields)}]: ").strip()
                try:
                    f_idx = int(f_idx_str) - 1
                    if 0 <= f_idx < len(fields):
                        selected = fields[f_idx]
                        field_uuid = selected.id
                        geom_data = selected.boundary
                        lot_name = selected.name
                        default_ha = selected.area_hectares or 150.0
                        print(f"  ✓ Campo '{lot_name}' seleccionado ({default_ha:.2f} ha registradas).")
                except ValueError:
                    print("  Opción no válida. Usando polígono por defecto.")
            else:
                print(f"  {S.DIM}No se encontraron campos en la base de datos. Usando polígono por defecto.{S.RESET}")
                geom_data = _box_from_centroid(-32.70, -62.10, 500.0)

        # Paso 3: Superficie
        print(f"\n{S.BOLD}{S.BRIGHT_CYAN}[Paso 3 de 5]{S.RESET} {S.BOLD}Superficie del Campo a Valuar (Hectáreas):{S.RESET}")
        print(f"  {S.DIM}Especifica las hectáreas totales del lote (detectadas automáticamente: {default_ha:.2f} ha){S.RESET}")
        ha_str = input(f"  > Hectáreas del lote [{default_ha:.2f}]: ").strip()
        try:
            surface_ha = float(ha_str) if ha_str else default_ha
        except ValueError:
            surface_ha = default_ha

        if geom_data is None and field_uuid is None:
            geom_data = _box_from_centroid(lat, lon, surface_ha)

        # Paso 4: Años
        print(f"\n{S.BOLD}{S.BRIGHT_CYAN}[Paso 4 de 5]{S.RESET} {S.BOLD}Horizonte de Proyección Temporal:{S.RESET}")
        years_str = input("  > Años a proyectar a futuro (1 a 20 años) [5]: ").strip()
        try:
            projection_years = max(1, min(20, int(years_str))) if years_str else 5
        except ValueError:
            projection_years = 5

        # Paso 5: Modo de consulta
        print(f"\n{S.BOLD}{S.BRIGHT_CYAN}[Paso 5 de 5]{S.RESET} {S.BOLD}Conectividad y Auditoría:{S.RESET}")
        net_str = input("  > ¿Consultar APIs externas en tiempo real (IDECOR y OpenStreetMap)? (S/n) [S]: ").strip().lower()
        allow_network = net_str not in ["n", "no", "false", "0"]

        # Ejecución del pipeline con feedback interactivo
        print(f"\n{S.BRIGHT_YELLOW}════════════════════════════════════════════════════════════════════════════════{S.RESET}")
        print(f"{S.BOLD}🚀 EJECUTANDO PIPELINE DE VALUACIÓN EN TIEMPO REAL...{S.RESET}")
        print(f"{S.BRIGHT_YELLOW}════════════════════════════════════════════════════════════════════════════════{S.RESET}")

        c_lat, c_lon, surface_calc, _ = parse_geometry_input(geom_data)
        time.sleep(0.15)

        print(f"  {S.CYAN}[1/4] 📍 Resolviendo Catastro y Perfil Edafológico (T0)...{S.RESET}", end="", flush=True)
        base_info = fetch_base_land_value(c_lat, c_lon, allow_network=allow_network)
        print(f" {S.BRIGHT_GREEN}✓{S.RESET} {S.DIM}(Dpto. {base_info.get('department')}, Base: USD {base_info.get('base_value_usd_ha'):,.2f}/ha){S.RESET}")

        print(f"  {S.CYAN}[2/4] 🛣️  Analizando Infraestructura Vial en 50 km (OSM)...{S.RESET}", end="", flush=True)
        log_driver = calculate_logistic_multiplier(c_lat, c_lon, allow_network=allow_network)
        print(f" {S.BRIGHT_GREEN}✓{S.RESET} {S.DIM}(Impacto logístico: {log_driver.impact_percentage:+.1f}%, Factor: {log_driver.multiplier:.3f}x){S.RESET}")

        print(f"  {S.CYAN}[3/4] 🌾 Procesando 15 Años de Series Históricas SAGyP...{S.RESET}", end="", flush=True)
        agro_driver = calculate_agronomic_multiplier(c_lat, c_lon, projection_years, allow_network=allow_network)
        print(f" {S.BRIGHT_GREEN}✓{S.RESET} {S.DIM}(CAGR anual: +{agro_driver.cagr_annual_pct:.2f}%, Factor: {agro_driver.multiplier:.3f}x){S.RESET}")

        print(f"  {S.CYAN}[4/4] 🔐 Componiendo Ecuación, ROI y Certificado SHA-256...{S.RESET}", end="", flush=True)
        res = run_land_valuation_projection(
            geometry_data=geom_data,
            lot_name=lot_name,
            projection_years=projection_years,
            field_id=field_uuid,
            surface_ha=surface_ha,
            include_audit=True,
            allow_network=allow_network,
        )
        print(f" {S.BRIGHT_GREEN}✓{S.RESET}")

        # Renderizar informe completo
        render_single_valuation(res, include_audit=True)

        # Preguntar si desea continuar o salir
        print(f"{S.BOLD}Opciones siguientes:{S.RESET}")
        print("  1) Evaluar otro campo / probar otro escenario")
        print("  2) Ver la tabla comparativa de todas las regiones argentinas")
        print("  3) Salir")
        next_op = input("  > Selecciona (1, 2 o 3) [1]: ").strip() or "1"

        if next_op == "2":
            compare_all_presets(years=projection_years, allow_network=allow_network)
            repeat = input("  > ¿Deseas hacer una nueva consulta? (s/N): ").strip().lower()
            if repeat not in ["s", "si", "y", "yes"]:
                print(f"\n{S.BRIGHT_GREEN}¡Gracias por utilizar el Proyector de Valor de Tierra de TERRIA! 🌱{S.RESET}\n")
                break
        elif next_op == "3":
            print(f"\n{S.BRIGHT_GREEN}¡Gracias por utilizar el Proyector de Valor de Tierra de TERRIA! 🌱{S.RESET}\n")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI del Proyector de Valor de Tierra a 5 Años (TERRIA FinTech & Real Estate)"
    )
    parser.add_argument("-i", "--interactive", action="store_true", help="Iniciar asistente interactivo guiado por consola")
    parser.add_argument("--field-id", type=str, help="UUID del campo persistido en SQLiteFieldStore")
    parser.add_argument(
        "--preset",
        type=str,
        choices=list(PRESETS.keys()),
        help="Preset agrícola (marcos_juarez, pergamino, venado_tuerto, federacion, charata, tres_arroyos)",
    )
    parser.add_argument("-c", "--compare-all", action="store_true", help="Comparar todos los presets regionales en una sola matriz")
    parser.add_argument("--lat", type=float, help="Latitud del centroide del campo (ej: -32.70)")
    parser.add_argument("--lon", type=float, help="Longitud del centroide del campo (ej: -62.10)")
    parser.add_argument("--ha", type=float, default=None, help="Superficie del lote en hectáreas")
    parser.add_argument("--geojson", type=str, help="Geometría en formato GeoJSON Polygon")
    parser.add_argument("--coords", type=str, help="Puntos en formato 'lon,lat;lon,lat;...'")
    parser.add_argument("--name", type=str, default=None, help="Nombre del lote")
    parser.add_argument("--years", type=int, default=5, help="Años de proyección (default: 5)")
    parser.add_argument("--audit", action="store_true", default=True, help="Mostrar enlaces de auditoría externa")
    parser.add_argument("--offline", "--fast", action="store_true", help="Modo rápido offline (sin consultas HTTP externas)")
    parser.add_argument("--json", action="store_true", help="Emitir el resultado estructurado en formato JSON")
    parser.add_argument("--no-color", action="store_true", help="Desactivar colores ANSI en la terminal")

    args = parser.parse_args()

    if args.no_color:
        global USE_COLOR
        USE_COLOR = False

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Si se invoca con -i o sin argumentos en una terminal interactiva, lanzar el wizard
    no_args_given = len(sys.argv) == 1
    if args.interactive or (no_args_given and sys.stdin.isatty()):
        run_interactive_wizard()
        return

    allow_network = not args.offline

    # Modo matriz comparativa
    if args.compare_all:
        compare_all_presets(years=args.years, allow_network=allow_network)
        return

    field_uuid = None
    default_ha = 500.0

    if args.preset:
        p = PRESETS[args.preset]
        lot_name = args.name or p["name"]
        surface = args.ha if args.ha is not None else p["ha"]
        geom_data = _box_from_centroid(p["lat"], p["lon"], surface)
    elif args.field_id:
        store = get_field_store()
        try:
            f_uuid = UUID(args.field_id)
            stored = store.get(f_uuid)
            geom_data = stored.value.boundary
            lot_name = args.name or stored.value.name
            field_uuid = f_uuid
        except Exception as e:
            print(f"Error al cargar campo con ID {args.field_id}: {e}")
            sys.exit(1)
    elif args.lat is not None and args.lon is not None:
        surface = args.ha if args.ha is not None else default_ha
        lot_name = args.name or f"Lote ({args.lat:.4f}, {args.lon:.4f})"
        geom_data = _box_from_centroid(args.lat, args.lon, surface)
    elif args.geojson:
        try:
            geom_data = json.loads(args.geojson)
            lot_name = args.name or "Lote GeoJSON"
        except Exception as e:
            print(f"Error al parsear GeoJSON: {e}")
            sys.exit(1)
    elif args.coords:
        pairs = []
        for pair in args.coords.split(";"):
            parts = [float(x.strip()) for x in pair.split(",") if x.strip()]
            if len(parts) >= 2:
                pairs.append([parts[0], parts[1]])
        geom_data = pairs
        lot_name = args.name or "Lote Coordenadas"
    else:
        # Default: Marcos Juárez, Córdoba
        lot_name = args.name or "Lote Marcos Juárez (Zona Núcleo - Córdoba)"
        surface = args.ha if args.ha is not None else default_ha
        geom_data = _box_from_centroid(-32.70, -62.10, surface)

    if not args.json:
        print(f"\n{Style.CYAN}[*] Procesando valuación de tierra a {args.years} años para '{lot_name}'...{Style.RESET}")

    surface_arg = args.ha if args.ha is not None else (surface if "surface" in locals() else None)
    res = run_land_valuation_projection(
        geometry_data=geom_data,
        lot_name=lot_name,
        projection_years=args.years,
        field_id=field_uuid,
        surface_ha=surface_arg,
        include_audit=args.audit,
        allow_network=allow_network,
    )

    if args.json:
        print(json.dumps(res.model_dump(mode="json"), indent=2, ensure_ascii=False))
    else:
        render_single_valuation(res, include_audit=args.audit)


if __name__ == "__main__":
    main()
