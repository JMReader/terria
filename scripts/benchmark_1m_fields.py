from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections import Counter
from typing import Any

from app.valuation.agronomic_trend import calculate_agronomic_multiplier
from app.valuation.idecor import fetch_base_land_value
from app.valuation.vialidad import calculate_logistic_multiplier


def generate_random_argentine_field(idx: int) -> tuple[str, float, float, float]:
    # Ponderacion por regiones agropecuarias argentinas
    # 45% Pampa Humeda / Centro, 18% NEA/Chaco, 12% Mesopotamia, 10% NOA, 8% Cuyo/Pampa Seca, 7% Patagonia
    region_choice = random.random()
    if region_choice < 0.45:
        # Pampa Humeda (Buenos Aires, Cordoba, Santa Fe)
        lat = random.uniform(-38.5, -31.0)
        lon = random.uniform(-64.5, -58.5)
    elif region_choice < 0.63:
        # NEA / Chaco / Santiago del Estero
        lat = random.uniform(-29.5, -24.5)
        lon = random.uniform(-64.5, -58.5)
    elif region_choice < 0.75:
        # Mesopotamia (Entre Rios, Corrientes, Misiones)
        lat = random.uniform(-33.5, -26.0)
        lon = random.uniform(-59.5, -54.0)
    elif region_choice < 0.85:
        # NOA (Salta, Tucuman, Jujuy, Catamarca, La Rioja)
        lat = random.uniform(-28.5, -22.5)
        lon = random.uniform(-66.8, -63.5)
    elif region_choice < 0.93:
        # Cuyo & Pampa Seca (Mendoza, San Juan, San Luis, La Pampa)
        lat = random.uniform(-38.0, -31.5)
        lon = random.uniform(-69.0, -64.5)
    else:
        # Patagonia (Rio Negro, Neuquen, Chubut, Santa Cruz, Tierra del Fuego)
        lat = random.uniform(-54.5, -38.5)
        lon = random.uniform(-71.5, -63.5)

    surface_ha = round(random.uniform(15.0, 3500.0), 2)
    lot_name = f'Lote-Sim-{idx:07d}'
    return lot_name, lat, lon, surface_ha


def run_benchmark(total_fields: int = 1_000_000):
    print(f'=== INICIANDO BENCHMARK MASIVO: {total_fields:,} CAMPOS ALEATORIOS EN ARGENTINA ===')
    random.seed(2026)
    t_start = time.time()

    errors_count = 0
    exceptions_list = []
    hash_set = set()
    hash_collisions = 0

    provinces_counter = Counter()
    departments_counter = Counter()

    sample_rate = max(1, total_fields // 100_000)
    sampled_base_val = []
    sampled_proj_val = []
    sampled_m_log = []
    sampled_m_agro = []
    sampled_roi = []
    sampled_dist_paved = []
    sampled_cap_gain = []

    total_surface_sum = 0.0
    total_base_capital_sum = 0.0
    total_proj_capital_sum = 0.0
    total_gain_sum = 0.0

    print('Procesando lotes en lotes de 100,000...')

    for i in range(total_fields):
        if (i + 1) % 100_000 == 0:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed
            print(f'  -> Procesados {i+1:,} / {total_fields:,} campos ({((i+1)/total_fields)*100:.1f}%) a {rate:,.0f} campos/s')

        name, lat, lon, ha = generate_random_argentine_field(i)

        try:
            base_info = fetch_base_land_value(lat, lon, allow_network=False)
            v0 = base_info['base_value_usd_ha']
            prov = base_info['province']
            dept = base_info['department']

            log_driver = calculate_logistic_multiplier(lat, lon, allow_network=False)
            m_log = log_driver.multiplier
            dist_paved = log_driver.distance_to_current_paved_km

            agro_driver = calculate_agronomic_multiplier(lat, lon, projection_years=5, allow_network=False)
            m_agro = agro_driver.multiplier

            m_mkt = 1.1041

            v5 = round(v0 * m_log * m_agro * m_mkt, 2)
            roi_pct = round(((v5 - v0) / v0) * 100.0, 2)
            base_lot_usd = round(v0 * ha, 2)
            proj_lot_usd = round(v5 * ha, 2)
            cap_gain_usd = round(proj_lot_usd - base_lot_usd, 2)

            if math.isnan(v5) or math.isinf(v5) or v5 <= 0:
                errors_count += 1
                exceptions_list.append(f'Invalid V5: {v5} at ({lat}, {lon})')
            if m_log < 1.0 or m_log > 1.15:
                errors_count += 1
                exceptions_list.append(f'Invalid M_log: {m_log} at ({lat}, {lon})')
            if m_agro < 1.0:
                errors_count += 1
                exceptions_list.append(f'Invalid M_agro: {m_agro} at ({lat}, {lon})')

            payload_str = f'{name}|{lat:.4f}|{lon:.4f}|{ha}|{v0}|{v5}|{m_log}|{m_agro}'
            h = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
            if h in hash_set:
                hash_collisions += 1
            else:
                if len(hash_set) < 1_000_000:
                    hash_set.add(h)

            provinces_counter[prov] += 1
            departments_counter[(dept, prov)] += 1

            total_surface_sum += ha
            total_base_capital_sum += base_lot_usd
            total_proj_capital_sum += proj_lot_usd
            total_gain_sum += cap_gain_usd

            if i % sample_rate == 0:
                sampled_base_val.append(v0)
                sampled_proj_val.append(v5)
                sampled_m_log.append(m_log)
                sampled_m_agro.append(m_agro)
                sampled_roi.append(roi_pct)
                sampled_dist_paved.append(dist_paved)
                sampled_cap_gain.append(cap_gain_usd)

        except Exception as e:
            errors_count += 1
            if len(exceptions_list) < 20:
                exceptions_list.append(f'Exception at field {i}: {str(e)}')

    t_end = time.time()
    total_time = t_end - t_start
    throughput = total_fields / total_time

    def get_percentiles(arr):
        s = sorted(arr)
        n = len(s)
        return {
            'min': s[0],
            'p10': s[int(n * 0.10)],
            'p25': s[int(n * 0.25)],
            'median': s[int(n * 0.50)],
            'mean': round(sum(s) / n, 2),
            'p75': s[int(n * 0.75)],
            'p90': s[int(n * 0.90)],
            'max': s[-1],
        }

    stats_v0 = get_percentiles(sampled_base_val)
    stats_v5 = get_percentiles(sampled_proj_val)
    stats_log = get_percentiles(sampled_m_log)
    stats_agro = get_percentiles(sampled_m_agro)
    stats_roi = get_percentiles(sampled_roi)
    stats_dist = get_percentiles(sampled_dist_paved)

    results = {
        'total_fields': total_fields,
        'total_time_seconds': round(total_time, 2),
        'throughput_fields_per_second': round(throughput, 1),
        'errors_count': errors_count,
        'hash_collisions': hash_collisions,
        'unique_provinces_count': len(provinces_counter),
        'unique_departments_count': len(departments_counter),
        'provinces_distribution': dict(provinces_counter.most_common()),
        'top_departments': [
            {'department': d, 'province': p, 'count': c, 'pct': round((c / total_fields) * 100, 2)}
            for (d, p), c in departments_counter.most_common(20)
        ],
        'financial_aggregates': {
            'total_surface_ha': round(total_surface_sum, 2),
            'total_base_capital_usd': round(total_base_capital_sum, 2),
            'total_projected_capital_usd': round(total_proj_capital_sum, 2),
            'total_gain_usd': round(total_gain_sum, 2),
            'macro_portfolio_roi_pct': round(((total_proj_capital_sum - total_base_capital_sum) / total_base_capital_sum) * 100.0, 2),
        },
        'distributions': {
            'base_value_usd_ha': stats_v0,
            'projected_value_usd_ha': stats_v5,
            'logistic_multiplier': stats_log,
            'agronomic_multiplier': stats_agro,
            'roi_percentage': stats_roi,
            'distance_to_highway_km': stats_dist,
        },
        'exceptions': exceptions_list,
    }

    with open('benchmark_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print('\n=== BENCHMARK COMPLETADO EXITOSAMENTE ===')
    print(f'Tiempo Total: {total_time:.2f} segundos')
    print(f'Throughput: {throughput:,.1f} campos/segundo')
    print(f'Errores / Excepciones: {errors_count}')
    print(f'Colisiones SHA-256: {hash_collisions}')
    print(f'Provincias representadas: {len(provinces_counter)} de 23')
    print('Resultados guardados en benchmark_results.json')
    return results

if __name__ == '__main__':
    run_benchmark(1_000_000)