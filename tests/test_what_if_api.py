from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_simulation_benchmarks_list() -> None:
    response = client.get("/v1/simulations/what-if/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "benchmarks" in data
    benchmark_ids = [b["id"] for b in data["benchmarks"]]
    assert "inta_marcos_juarez" in benchmark_ids
    assert "entre_rios_mandisovi" in benchmark_ids


def test_field_coupled_simulation() -> None:
    # 1. Crear un campo en el store
    create_resp = client.post(
        "/v1/fields",
        json={
            "name": "Campo Federación Test",
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
        },
    )
    assert create_resp.status_code == 201
    field_id = create_resp.json()["id"]

    # 2. Ejecutar simulación What-If acoplada al campo
    sim_resp = client.post(
        f"/v1/fields/{field_id}/simulations/what-if",
        json={
            "target_year": 2023,
            "simulated_crop": "maiz",
            "real_crop": "soja_1ra",
            "real_margin_usd_ha": 350.0,
            "include_audit": True,
        },
    )
    assert sim_resp.status_code == 200
    res = sim_resp.json()

    assert res["status"] == "success"
    assert res["schema_version"] == "0.1"
    assert res["algorithm_version"] == "2.1.0"
    assert res["lot_name"] == "Campo Federación Test"
    assert res["surface_ha"] > 80.0  # El polígono tiene ~87.2 ha
    assert res["simulated_crop"] == "maiz"

    # Verificación de métricas del modelo y Lotes Gemelos
    metrics = res["model_metrics"]
    assert metrics["candidate_lots_scanned"] == 180
    assert metrics["strict_twin_lots_matched"] >= 5
    assert 0.0 <= metrics["avg_similarity_score"] <= 1.0

    # Verificación de resultados agronómicos y financieros
    results = res["results"]
    assert results["projected_yield_tn_ha"] > 0
    assert results["benchmark_dept_yield_tn_ha"] > 0
    assert "gross_income_usd_ha" in results["financials"]
    assert "net_margin_usd_ha" in results["financials"]
    assert "total_lot_diff_usd" in results["financials"]

    # Trazabilidad y anclaje on-chain (SHA-256)
    assert len(res["content_hash"]) == 64
    assert res["audit_urls"] is not None
    assert "copernicus_browser_sentinel2" in res["audit_urls"]
    assert "open_meteo_era5_reanalysis" in res["audit_urls"]


def test_field_simulation_not_found() -> None:
    non_existent = uuid4()
    response = client.post(
        f"/v1/fields/{non_existent}/simulations/what-if",
        json={
            "target_year": 2023,
            "simulated_crop": "maiz",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "FIELD_NOT_FOUND"


def test_standalone_simulation() -> None:
    response = client.post(
        "/v1/simulations/what-if",
        json={
            "name": "Lote Ad-Hoc Marcos Juárez",
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
            "target_year": 2023,
            "simulated_crop": "soja_1ra",
            "real_crop": "maiz",
            "real_margin_usd_ha": 600.0,
        },
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["lot_name"] == "Lote Ad-Hoc Marcos Juárez"
    assert len(res["content_hash"]) == 64


def test_truth_verification_endpoint() -> None:
    response = client.post(
        "/v1/simulations/what-if/verify",
        json={
            "benchmark_id": "inta_marcos_juarez",
            "target_year": 2023,
            "crop": "maiz",
        },
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "verified"
    assert "INTA EEA Marcos Juárez" in res["benchmark"]
    assert res["dimensions"]["soil"]["clay_pct"] == 24.2
    assert len(res["content_hash"]) == 64
    assert "copernicus_browser_sentinel2" in res["audit_urls"]
