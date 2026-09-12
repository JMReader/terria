from __future__ import annotations

import argparse
import json
import math
import sys
from uuid import UUID

from app.store import SQLiteFieldStore
from app.valuation.engine import run_land_valuation_projection

PRESETS = {
    "marcos_juarez": {
        "name": "Lote Marcos Juárez (Zona Núcleo)",
        "lat": -32.70,
        "lon": -62.10,
        "ha": 500.0,
    },
    "pergamino": {
        "name": "Lote Pergamino (Pampa Húmeda)",
        "lat": -33.89,
        "lon": -60.57,
        "ha": 420.0,
    },
    "venado_tuerto": {
        "name": "Lote Venado Tuerto (Maicera)",
        "lat": -33.74,
        "lon": -61.96,
        "ha": 650.0,
    },
    "federacion": {
        "name": "Lote Federación Mandisoví (Entre Ríos)",
        "lat": -30.98,
        "lon": -57.92,
        "ha": 280.0,
    },
    "charata": {
        "name": "Lote Charata (Región Chaqueña)",
        "lat": -27.21,
        "lon": -61.19,
        "ha": 1200.0,
    },
    "tres_arroyos": {
        "name": "Lote Tres Arroyos (Pampa Sur)",
        "lat": -38.37,
        "lon": -60.27,
        "ha": 800.0,
    },
}


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI del Proyector de Valor de Tierra a 5 Años (TERRIA FinTech & Real Estate)"
    )
    parser.add_argument("--field-id", type=str, help="UUID del campo en SQLiteFieldStore")
    parser.add_argument("--preset", type=str, choices=list(PRESETS.keys()), help="Preset agrícola (marcos_juarez, pergamino, venado_tuerto, federacion, charata, tres_arroyos)")
    parser.add_argument("--lat", type=float, help="Latitud del centroide del campo (ej: -32.70)")
    parser.add_argument("--lon", type=float, help="Longitud del centroide del campo (ej: -62.10)")
    parser.add_argument("--ha", type=float, default=500.0, help="Superficie del lote en hectáreas (default: 500)")
    parser.add_argument("--geojson", type=str, help="Geometría en formato GeoJSON Polygon")
    parser.add_argument("--coords", type=str, help="Puntos en formato 'lon,lat;lon,lat;...'")
    parser.add_argument("--name", type=str, default=None, help="Nombre del lote")
    parser.add_argument("--years", type=int, default=5, help="Años de proyección (default: 5)")
    parser.add_argument("--audit", action="store_true", help="Mostrar enlaces de auditoría externa")

    args = parser.parse_args()

    field_uuid = None
    if args.preset:
        p = PRESETS[args.preset]
        lot_name = args.name or p["name"]
        geom_data = _box_from_centroid(p["lat"], p["lon"], args.ha if args.ha != 500.0 else p["ha"])
    elif args.field_id:
        store = SQLiteFieldStore()
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
        lot_name = args.name or f"Lote ({args.lat:.4f}, {args.lon:.4f})"
        geom_data = _box_from_centroid(args.lat, args.lon, args.ha)
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
        lot_name = args.name or "Lote Marcos Juárez (Zona Núcleo)"
        geom_data = _box_from_centroid(-32.70, -62.10, args.ha)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"\n[*] Ejecutando proyección de valor a {args.years} años para '{lot_name}'...")
    res = run_land_valuation_projection(
        geometry_data=geom_data,
        lot_name=lot_name,
        projection_years=args.years,
        field_id=field_uuid,
        include_audit=args.audit or True,
    )

    v = res.valuation
    print("\n" + "=" * 80)
    print(f" PROYECCIÓN DE VALOR DE TIERRA A {v.projection_years} AÑOS: {res.lot_name.upper()}")
    print("=" * 80)
    print(f"Superficie Evaluada: {v.financial_totals.surface_ha:.2f} hectáreas")
    print(f"Horizonte Temporal:  {v.current_year} -> {v.target_year} ({v.projection_years} años)")
    print(f"Valor Base Actual:   USD {v.base_value_usd_ha:,.2f} / ha")
    print(f"Valor Proyectado:    USD {v.projected_value_usd_ha:,.2f} / ha")
    print(f"Apreciación Total:   +{v.total_appreciation_percentage:.1f}% (ROI Pasivo Esperado)")

    cagr_eff = ((v.projected_value_usd_ha / v.base_value_usd_ha) ** (1.0 / v.projection_years) - 1.0) * 100.0
    print(f"CAGR Efectivo:       +{cagr_eff:.2f}% / año")


    print("\n" + "-" * 80)
    print(" DESGLOSE DE LOS 3 MOTORES DE VALOR (DRIVERS)")
    print("-" * 80)
    log = v.drivers_breakdown.logistic_improvement
    print("1. INFRAESTRUCTURA & LOGÍSTICA VIAL:")
    print(f"   * Impacto: +{log.impact_percentage:.1f}%  |  Multiplicador: {log.multiplier:.4f}x")
    print(f"   * Distancia actual al asfalto: {log.distance_to_current_paved_km:.1f} km")
    print(f"   * Distancia con nueva traza:   {log.distance_to_future_paved_km:.1f} km (Ahorro: {log.distance_saved_km:.1f} km)")
    print(f"   * Detalle: {log.detail}")

    agro = v.drivers_breakdown.agronomic_trend
    print("\n2. PRODUCTIVIDAD AGRONÓMICA & SUELO (SAGyP 15 AÑOS):")
    print(f"   * Impacto: +{agro.impact_percentage:.1f}%  |  Multiplicador: {agro.multiplier:.4f}x")
    print(f"   * CAGR histórico departamental: +{agro.cagr_annual_pct:.2f}% / año")
    print(f"   * Detalle: {agro.detail}")

    mkt = v.drivers_breakdown.market_appreciation
    print("\n3. MERCADO INMOBILIARIO RURAL (REFUGIO EN USD):")
    print(f"   * Impacto: +{mkt.impact_percentage:.1f}%  |  Multiplicador: {mkt.multiplier:.4f}x")
    print(f"   * Tasa macro inmobiliaria: +{mkt.annual_rate_pct:.2f}% / año")
    print(f"   * Detalle: {mkt.detail}")

    print("\n" + "-" * 80)
    print(" TOTALES FINANCIEROS DE CARTERA")
    print("-" * 80)
    fin = v.financial_totals
    print(f"Valor Total del Lote Hoy ({v.current_year}):        USD {fin.total_base_value_usd:,.2f}")
    print(f"Valor Total del Lote Proyectado ({v.target_year}): USD {fin.total_projected_value_usd:,.2f}")
    print(f"GANANCIA DE CAPITAL PATRIMONIAL:          USD {fin.total_capital_gain_usd:+,.2f}")

    print("\n" + "-" * 80)
    print(" CERTIFICACIÓN CRIPTOGRÁFICA ON-CHAIN (SOLANA READY)")
    print("-" * 80)
    print(f"SHA-256 Content Hash: {v.content_hash}")

    if v.audit_urls:
        print("\nENLACES Y FUENTES DE AUDITORÍA PÚBLICA:")
        for k, u in v.audit_urls.items():
            print(f"  * [{k}]: {u}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

