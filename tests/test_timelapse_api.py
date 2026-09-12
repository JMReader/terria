from __future__ import annotations


from fastapi.testclient import TestClient

from app.main import app
from app.timelapse.cli import seed_demo

client = TestClient(app)


def test_debug_timelapse_page_returns_html() -> None:
    res = client.get("/debug/timelapse")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "TERRIA" in res.text
    assert "timeline-slider" in res.text
    assert "json-viewer" in res.text


def test_boundary_update_bug_fix() -> None:
    """Verifies that updating boundary does not raise AttributeError and recalculates area."""
    created = client.post(
        "/v1/fields",
        json={
            "name": "Lote Test Area",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-64.2, -32.9], [-64.1, -32.9], [-64.1, -32.8], [-64.2, -32.9]]],
            },
        },
    )
    assert created.status_code == 201
    field_id = created.json()["id"]

    # Update boundary with new coordinates
    updated = client.patch(
        f"/v1/fields/{field_id}",
        json={
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-64.3, -32.9], [-64.1, -32.9], [-64.1, -32.7], [-64.3, -32.9]]],
            }
        },
    )
    assert updated.status_code == 200
    assert updated.json()["area_hectares"] > 0


def test_seed_demo_and_api_contract_flow() -> None:
    """End-to-end integration test with seeded demo and real datasets."""
    # Seed datasets
    seed_demo()

    # List fields
    res_fields = client.get("/v1/fields")
    assert res_fields.status_code == 200
    fields = res_fields.json()
    demo_field = next(f for f in fields if "La Posta" in f["name"])
    field_id = demo_field["id"]

    # List datasets for field
    res_datasets = client.get(f"/v1/fields/{field_id}/timelapses")
    assert res_datasets.status_code == 200
    datasets = res_datasets.json()
    assert len(datasets) >= 2

    # Find the synthetic demo dataset and real dataset
    demo_ds = next(d for d in datasets if d["is_demo"] is True)
    real_ds = next(d for d in datasets if d["is_demo"] is False)

    # 1. Test Demo Dataset Manifest
    res_manifest = client.get(f"/v1/fields/{field_id}/timelapses/{demo_ds['id']}")
    assert res_manifest.status_code == 200
    manifest = res_manifest.json()
    assert manifest["dataset_id"] == demo_ds["id"]
    assert manifest["is_demo"] is True
    assert len(manifest["frames"]) > 0
    assert len(manifest["weather_daily"]) > 0

    # 2. Test Timeline State Endpoint
    target_date = "2024-02-15"
    res_state = client.get(
        f"/v1/fields/{field_id}/timelapses/{demo_ds['id']}/timeline-state?date={target_date}"
    )
    assert res_state.status_code == 200
    state = res_state.json()
    assert state["selected_date"] == target_date
    assert state["dataset_id"] == demo_ds["id"]
    assert "weather" in state
    assert state["weather"]["date"] == target_date
    assert state["is_demo"] is True

    # 3. Test Frame Asset Image Delivery (RGB & NDVI PNG)
    frame = manifest["frames"][0]
    frame_id = frame["id"]
    res_rgb = client.get(
        f"/v1/fields/{field_id}/timelapses/{demo_ds['id']}/frames/{frame_id}/assets/rgb"
    )
    assert res_rgb.status_code == 200
    assert res_rgb.headers["content-type"] == "image/png"
    assert res_rgb.content[:8] == b"\x89PNG\r\n\x1a\n"

    res_ndvi = client.get(
        f"/v1/fields/{field_id}/timelapses/{demo_ds['id']}/frames/{frame_id}/assets/ndvi"
    )
    assert res_ndvi.status_code == 200
    assert res_ndvi.headers["content-type"] == "image/png"
    assert res_ndvi.content[:8] == b"\x89PNG\r\n\x1a\n"

    # 4. Test Real Dataset Manifest
    res_real_manifest = client.get(f"/v1/fields/{field_id}/timelapses/{real_ds['id']}")
    assert res_real_manifest.status_code == 200
    real_manifest = res_real_manifest.json()
    assert real_manifest["is_demo"] is False
    assert real_manifest["status"] in ("ready", "partial")
    assert len(real_manifest["weather_daily"]) > 0
    # Without CDSE credentials the dataset explains the missing satellite data; with configured
    # credentials it contains real Sentinel frames instead.
    if real_manifest["frames"]:
        assert all(frame["source_item_ids"] for frame in real_manifest["frames"])
    else:
        assert any("SATELLITE_CREDENTIALS_MISSING" in r for r in real_manifest["missing_reasons"])

    # 5. Test Publishing Timelapse
    # First publish field
    client.post(f"/v1/fields/{field_id}/publish")
    field_public_slug = client.get(f"/v1/fields/{field_id}").json()["public_slug"]

    # Publish demo dataset
    res_publish = client.post(f"/v1/fields/{field_id}/timelapses/{demo_ds['id']}/publish")
    assert res_publish.status_code == 200

    # Read public timelapse
    res_pub = client.get(f"/v1/public/fields/{field_public_slug}/timelapse")
    assert res_pub.status_code == 200
    pub_manifest = res_pub.json()
    assert pub_manifest["dataset_id"] == demo_ds["id"]
    assert "field_id" not in pub_manifest  # Private field_id omitted from public manifest!


def test_post_timelapse_creates_job_or_returns_existing() -> None:
    # Create test field
    created = client.post(
        "/v1/fields",
        json={
            "name": "Campo Job Test",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-60.5, -33.5], [-60.4, -33.5], [-60.4, -33.4], [-60.5, -33.5]]],
            },
        },
    )
    field_id = created.json()["id"]

    # Request new timelapse
    res = client.post(
        f"/v1/fields/{field_id}/timelapses",
        json={
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "layers": ["rgb", "ndvi"],
            "is_demo": True,
        },
    )
    assert res.status_code in (200, 202)
    if res.status_code == 202:
        job_id = res.json()["id"]
        res_job = client.get(f"/v1/timelapse-jobs/{job_id}")
        assert res_job.status_code == 200
        assert res_job.json()["status"] in ("queued", "processing", "ready")
