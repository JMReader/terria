from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from app.store import SQLiteFieldStore
from app.what_if.engine import run_what_if_simulation
from app.what_if.router import verify_simulation_truth
from app.what_if.schemas import VerificationRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI del Simulador Agronómico Retrospectivo What-If (TERRIA v2.1)"
    )
    parser.add_argument("--field-id", type=str, help="UUID del campo en SQLiteFieldStore")
    parser.add_argument("--geojson", type=str, help="Geometría en formato GeoJSON")
    parser.add_argument("--coords", type=str, help="Puntos en formato 'lon,lat;lon,lat;...'")
    parser.add_argument("--name", type=str, default="Lote Evaluación", help="Nombre del lote")
    parser.add_argument("--year", type=int, default=2023, help="Campaña agrícola (ej: 2023)")
    parser.add_argument("--crop", type=str, default="maiz", help="Cultivo simulado")
    parser.add_argument("--real-crop", type=str, default="soja_1ra", help="Cultivo real cosechado")
    parser.add_argument("--real-margin", type=float, default=350.0, help="Margen real en USD/ha")
    parser.add_argument("--benchmark", type=str, help="Verificar benchmark (inta_marcos_juarez | entre_rios_mandisovi)")
    parser.add_argument("--audit", action="store_true", help="Mostrar URLs de auditoría pública")

    args = parser.parse_args()

    # Modo Benchmark
    if args.benchmark:
        req = VerificationRequest(benchmark_id=args.benchmark, target_year=args.year, crop=args.crop)
        res = verify_simulation_truth(req)
        print("\n" + "=" * 80)
        print(f" CONTROL DE VERACIDAD: {res.benchmark}")
        print("=" * 80)
        print(f"Coordenadas: Lat {res.coordinates['latitude']}, Lon {res.coordinates['longitude']}")
        print(f"Campaña:     {args.year}")
        print(f"Veredicto:   {res.verdict}")
        print(f"SHA-256:     {res.content_hash}\n")
        print("--- DIMENSIONES FÍSICAS MEDIDAS ---")
        for k, v in res.dimensions.items():
            print(f"[{k.upper()}]: {v}")
        if args.audit or True:
            print("\n--- ENLACES DE AUDITORÍA PÚBLICA ---")
            for k, u in res.audit_urls.items():
                print(f"  * {k}: {u}")
        return

    # Modo Campo Persistido
    if args.field_id:
        store = SQLiteFieldStore()
        try:
            f_uuid = UUID(args.field_id)
            stored = store.get(f_uuid)
            geom_data = stored.value.boundary
            lot_name = stored.value.name
            field_uuid = f_uuid
        except Exception as e:
            print(f"Error al cargar campo con ID {args.field_id}: {e}")
            sys.exit(1)
    elif args.geojson:
        try:
            geom_data = json.loads(args.geojson)
            lot_name = args.name
            field_uuid = None
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
        lot_name = args.name
        field_uuid = None
    else:
        # Por defecto lote Federación
        geom_data = [
            [-58.053002, -30.743134],
            [-58.044891, -30.736454],
            [-58.038368, -30.741805],
            [-58.045578, -30.747746],
            [-58.053002, -30.743134],
        ]
        lot_name = args.name
        field_uuid = None

    print(f"\n[*] Ejecutando simulación What-If para '{lot_name}'...")
    res = run_what_if_simulation(
        geometry_data=geom_data,
        lot_name=lot_name,
        target_year=args.year,
        simulated_crop=args.crop,
        real_crop=args.real_crop,
        real_margin_usd_ha=args.real_margin,
        field_id=field_uuid,
        include_audit=args.audit,
    )

    print("\n" + "=" * 80)
    print(f" RESULTADO SIMULACIÓN WHAT-IF: {res.lot_name.upper()} ({res.surface_ha:.2f} ha)")
    print("=" * 80)
    print(f"Campaña: {res.target_year} | Cultivo Simulado: {res.simulated_crop} | Cultivo Real: {res.real_crop}")
    print(f"Rinde Proyectado: {res.results.projected_yield_tn_ha:.2f} tn/ha (Oficial Dpto: {res.results.benchmark_dept_yield_tn_ha:.2f} tn/ha)")
    print(f"Margen Neto Proyectado: USD {res.results.financials.net_margin_usd_ha:.2f}/ha")
    print(f"Margen Neto Real:       USD {res.results.financials.real_net_margin_usd_ha:.2f}/ha")
    print(f"Diferencia Unitaria:    USD {res.results.financials.diff_net_margin_usd_ha:+.2f}/ha")
    print(f"DIFERENCIA TOTAL LOTE:  USD {res.results.financials.total_lot_diff_usd:+,.2f}")
    print(f"\nRecomendación: {res.results.recommendation}")
    print(f"SHA-256 Content Hash: {res.content_hash}")

    if res.audit_urls:
        print("\n--- ENLACES DE AUDITORÍA EXTERNA ---")
        for k, u in res.audit_urls.items():
            print(f"  * {k}: {u}")


if __name__ == "__main__":
    main()
