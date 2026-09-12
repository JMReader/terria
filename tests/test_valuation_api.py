from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_valuation_drivers_guide() -> None:
    response = client.get("/v1/valuations/drivers")
    assert response.status_code == 200
    data = response.json()
    assert "formula" in data
    assert "drivers" in data
    assert "M_log_logistic" in data["drivers"]
    assert "M_agro_agronomic" in data["drivers"]
    assert "M_mkt_market" in data["drivers"]


def test_field_coupled_valuation() -> None:
    # 1. Crear campo en Marcos Juárez
    create_resp = client.post(
        "/v1/fields",
        json={
            "name": "Estancia La Juanita",
            "boundary": {
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
            },
        },
    )
    assert create_resp.status_code == 201
    field_id = create_resp.json()["id"]

    # 2. Ejecutar proyección de valor a 5 años
    val_resp = client.post(
        f"/v1/fields/{field_id}/valuations/5yr",
        json={
            "projection_years": 5,
            "include_audit": True,
        },
    )
    assert val_resp.status_code == 200
    res = val_resp.json()

    assert res["status"] == "success"
    assert res["schema_version"] == "0.1"
    assert res["algorithm_version"] == "3.0.0"
    assert res["lot_name"] == "Estancia La Juanita"

    v = res["valuation"]
    assert v["current_year"] == 2026
    assert v["target_year"] == 2031
    assert v["projection_years"] == 5

    # Valores unitarios
    assert v["base_value_usd_ha"] >= 7000.0  # Zona Núcleo Marcos Juárez
    assert v["projected_value_usd_ha"] > v["base_value_usd_ha"]

    # Multiplicadores realistas calibrados
    drivers = v["drivers_breakdown"]
    assert 1.02 <= drivers["logistic_improvement"]["multiplier"] <= 1.15
    assert 1.02 <= drivers["agronomic_trend"]["multiplier"] <= 1.10
    assert 1.02 <= drivers["market_appreciation"]["multiplier"] <= 1.08

    # Apreciación total realista sin piso forzado ni sesgo inflado (AC-04: entre +9.5% y +13.5%)
    assert 9.5 <= v["total_appreciation_percentage"] <= 13.5

    # Totales del lote
    totals = v["financial_totals"]
    assert totals["surface_ha"] > 0
    assert totals["total_projected_value_usd"] > totals["total_base_value_usd"]
    assert totals["total_capital_gain_usd"] == round(
        totals["total_projected_value_usd"] - totals["total_base_value_usd"], 2
    )

    # Trazabilidad on-chain y auditoría
    assert len(v["content_hash"]) == 64
    assert v["audit_urls"] is not None
    assert "idecor_mapas_cordoba" in v["audit_urls"]
    assert "osm_overpass_vialidad" in v["audit_urls"]


def test_field_valuation_not_found() -> None:
    non_existent = uuid4()
    response = client.post(
        f"/v1/fields/{non_existent}/valuations/5yr",
        json={"projection_years": 5},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "FIELD_NOT_FOUND"


def test_standalone_valuation_entre_rios() -> None:
    response = client.post(
        "/v1/valuations/5yr",
        json={
            "name": "Lote Federación Mandisoví",
            "boundary": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-58.053002, -30.743134],
                        [-58.044891, -30.736454],
                        [-58.038368, -30.741805],
                        [-58.045578, -30.747746],
                        [-58.053002, -30.743134],
                    ]
                ],
            },
            "projection_years": 5,
        },
    )
    assert response.status_code == 200
    res = response.json()
    v = res["valuation"]

    assert res["lot_name"] == "Lote Federación Mandisoví"
    assert 3500.0 <= v["base_value_usd_ha"] <= 4500.0  # Valor dinámico calculado según capacidad edáfica
    assert v["projected_value_usd_ha"] > v["base_value_usd_ha"]
    assert v["financial_totals"]["surface_ha"] > 85.0
    assert len(v["content_hash"]) == 64


def test_valuation_custom_horizon_10_years() -> None:
    response = client.post(
        "/v1/valuations/5yr",
        json={
            "name": "Lote Inversión 10 Años",
            "projection_years": 10,
        },
    )
    assert response.status_code == 200
    v = response.json()["valuation"]
    assert v["current_year"] == 2026
    assert v["target_year"] == 2036
    assert v["projection_years"] == 10
    assert v["total_appreciation_percentage"] >= 18.0


def test_valuation_sensitivity_marcos_juarez_vs_pozo_del_carril() -> None:
    """AC-04: Verifica la diferenciación edafológica e hídrica real entre Zona Núcleo y Pedemonte."""
    from app.valuation.engine import run_land_valuation_projection

    # 1. Marcos Juárez (Clase I + napa freática óptima 1.8m)
    res_mj = run_land_valuation_projection(
        geometry_data=[[-62.1013, -32.7057], [-62.0907, -32.7057], [-62.0907, -32.7193], [-62.1013, -32.7193], [-62.1013, -32.7057]],
        lot_name="Marcos Juárez Test",
        projection_years=5,
        allow_network=False,
    )
    # 2. Pozo del Carril (Pedemonte Comechingones sin aporte freático)
    res_pc = run_land_valuation_projection(
        geometry_data=[[-64.6120, -32.9619], [-64.6014, -32.9619], [-64.6014, -32.9737], [-64.6120, -32.9737], [-64.6120, -32.9619]],
        lot_name="Pozo del Carril Test",
        projection_years=5,
        allow_network=False,
    )

    apprec_mj = res_mj.valuation.total_appreciation_percentage
    apprec_pc = res_pc.valuation.total_appreciation_percentage

    # Brecha de valor agronómica: Marcos Juárez aprecia más del doble que Pozo del Carril
    assert 9.5 <= apprec_mj <= 13.5
    assert 3.0 <= apprec_pc <= 5.5
    assert apprec_mj > apprec_pc


def test_valuation_mathematical_consistency_and_hash() -> None:
    """Verifica consistencia exacta de la ecuación maestra y determinismo del hash SHA-256."""
    from app.valuation.engine import run_land_valuation_projection

    res = run_land_valuation_projection(
        geometry_data=[[-60.57, -33.89], [-60.55, -33.89], [-60.55, -33.87], [-60.57, -33.87], [-60.57, -33.89]],
        lot_name="Pergamino Math Test",
        projection_years=5,
        allow_network=False,
    )
    v = res.valuation
    d = v.drivers_breakdown

    expected_proj = round(
        v.base_value_usd_ha * d.logistic_improvement.multiplier * d.agronomic_trend.multiplier * d.market_appreciation.multiplier,
        2,
    )
    assert v.projected_value_usd_ha == expected_proj
    assert len(v.content_hash) == 64

    # Re-ejecución determinista idéntica
    res2 = run_land_valuation_projection(
        geometry_data=[[-60.57, -33.89], [-60.55, -33.89], [-60.55, -33.87], [-60.57, -33.87], [-60.57, -33.89]],
        lot_name="Pergamino Math Test",
        projection_years=5,
        allow_network=False,
    )
    assert res2.valuation.content_hash == v.content_hash


def test_valuation_cli_preset(monkeypatch) -> None:
    from app.valuation.cli import main
    import sys

    monkeypatch.setattr(sys, "argv", ["cli.py", "--preset", "marcos_juarez", "--offline", "--years", "5"])
    # Debe ejecutarse sin lanzar excepciones
    main()


def test_valuation_cli_compare_all(monkeypatch) -> None:
    from app.valuation.cli import main
    import sys

    monkeypatch.setattr(sys, "argv", ["cli.py", "--compare-all", "--offline", "--years", "5"])
    main()


def test_valuation_cli_json_output(monkeypatch, capsys) -> None:
    from app.valuation.cli import main
    import json
    import sys

    monkeypatch.setattr(sys, "argv", ["cli.py", "--preset", "pergamino", "--offline", "--json"])
    main()
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["status"] == "success"
    assert "valuation" in parsed



