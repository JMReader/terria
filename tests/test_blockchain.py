from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.blockchain.canonical import CanonicalizationError, content_hash
from app.blockchain.payload import build_memo, parse_memo
from app.blockchain.snapshot import build_observations, build_sources
from app.main import app
from app.schemas import PolygonGeometry
from app.timelapse.monthly import build_monthly_series, campaign_of
from app.timelapse.schemas import (
    NdviMetrics,
    TimelapseFrame,
    TimelapseManifest,
    TimelapseSource,
    WeatherDaily,
)

client = TestClient(app)


def _create_field(name: str = "Lote Certificación") -> str:
    response = client.post(
        "/v1/fields",
        json={
            "name": name,
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-64.2, -32.9], [-64.1, -32.9], [-64.1, -32.8], [-64.2, -32.9]]],
            },
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_jcs_is_order_independent() -> None:
    first = content_hash({"b": 1, "a": 2, "c": {"z": 1, "y": 2}})
    second = content_hash({"c": {"y": 2, "z": 1}, "a": 2, "b": 1})
    assert first == second


def test_floats_are_rejected() -> None:
    try:
        content_hash({"ndvi": 0.71})
    except CanonicalizationError:
        return
    raise AssertionError("canonical hashing must reject floats")


def test_memo_roundtrip() -> None:
    digest = "a" * 64
    previous = "b" * 64
    parsed = parse_memo(build_memo("cert-1", digest, previous))
    assert parsed == {
        "format_version": "v1",
        "cert_uid": "cert-1",
        "content_hash": digest,
        "prev_hash": previous,
    }


def test_issue_and_verify_local_certification() -> None:
    field_id = _create_field()
    response = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2018, "period_to": 2026},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "anchored"
    assert body["version"] == 1
    assert len(body["content_hash"]) == 64
    assert body["anchor"]["provider"] == "local"
    assert body["anchor"]["tx_signature"]

    verification = client.get(f"/v1/public/certifications/{body['cert_uid']}/verify")
    assert verification.status_code == 200
    verified = verification.json()
    assert verified["status"] == "verified"
    assert verified["recomputed_hash"] == body["content_hash"]
    assert verified["on_chain_memo"].startswith("TERRIA1|v1|")


def test_second_certification_chains_previous_hash() -> None:
    field_id = _create_field("Lote Versiones")
    first = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2018, "period_to": 2025},
    ).json()
    second = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2018, "period_to": 2026},
    ).json()
    assert second["version"] == first["version"] + 1
    assert second["prev_content_hash"] == first["content_hash"]
    assert second["content_hash"] != first["content_hash"]


def test_list_and_detail_certifications() -> None:
    field_id = _create_field("Lote Listado")
    created = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2020, "period_to": 2026},
    ).json()

    listed = client.get(f"/v1/fields/{field_id}/certifications")
    assert listed.status_code == 200
    assert any(item["cert_uid"] == created["cert_uid"] for item in listed.json())

    detail = client.get(f"/v1/certifications/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["cert_uid"] == created["cert_uid"]


def test_public_certification_document() -> None:
    field_id = _create_field("Lote Documento")
    created = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2024, "period_to": 2026},
    ).json()

    response = client.get(f"/v1/public/certifications/{created['cert_uid']}")
    assert response.status_code == 200
    document = response.json()
    assert document["cert_uid"] == created["cert_uid"]
    assert document["version"] == 1
    assert document["verification_status"] == "verified"
    assert document["field"]["id"] == field_id
    assert document["content_hash"] == created["content_hash"]
    assert document["anchor"]["tx_signature"]
    assert document["snapshot"]["schema_version"] == document["schema_version"]
    assert "monthly" in document["snapshot"]


def test_public_certification_pdf() -> None:
    field_id = _create_field("Lote PDF")
    created = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2024, "period_to": 2026},
    ).json()

    response = client.get(f"/v1/public/certifications/{created['cert_uid']}.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_verify_unknown_certification_returns_404() -> None:
    response = client.get("/v1/public/certifications/does-not-exist/verify")
    assert response.status_code == 404


def test_public_certification_document_unknown_returns_404() -> None:
    response = client.get("/v1/public/certifications/does-not-exist")
    assert response.status_code == 404


def test_public_certification_pdf_unknown_returns_404() -> None:
    response = client.get("/v1/public/certifications/does-not-exist.pdf")
    assert response.status_code == 404


def test_invalid_period_is_rejected() -> None:
    field_id = _create_field("Lote Período")
    response = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2026, "period_to": 2018},
    )
    assert response.status_code == 422


def _manifest_with_observations() -> TimelapseManifest:
    return TimelapseManifest(
        dataset_id=uuid4(),
        processing_version="test",
        field_id=uuid4(),
        geometry_version_id=uuid4(),
        boundary=PolygonGeometry(
            type="Polygon", coordinates=[[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.0, 0.0]]]
        ),
        area_hectares=1.0,
        start_date=date(2024, 10, 1),
        end_date=date(2024, 10, 2),
        status="ready",
        generated_at=datetime(2024, 10, 2, tzinfo=timezone.utc),
        frames=[
            TimelapseFrame(
                id=uuid4(),
                observed_at=datetime(2024, 10, 2, tzinfo=timezone.utc),
                local_date=date(2024, 10, 2),
                usable=True,
                valid_area_fraction=1.0,
                ndvi=NdviMetrics(mean=0.4109, p10=0.171, p90=0.7404),
            )
        ],
        weather_daily=[
            WeatherDaily(
                date=date(2024, 10, 2),
                precipitation_mm=0.0,
                precipitation_7d_mm=0.0,
                temperature_min_c=10.4,
                temperature_max_c=21.3,
            )
        ],
        sources=[
            TimelapseSource(
                id="sentinel-2",
                provider="Copernicus CDSE",
                dataset="S2 L2A",
                retrieved_at=datetime(2024, 10, 2, tzinfo=timezone.utc),
                documentation_url="https://example.com",
                attribution="Copernicus",
            )
        ],
    )


def test_campaign_mapping() -> None:
    assert campaign_of("2024-10") == "2024/25"
    assert campaign_of("2025-03") == "2024/25"
    assert campaign_of("2025-04") == "2024/25"
    assert campaign_of("2025-08") == "2025/26"
    assert campaign_of("2026-01") == "2025/26"


def test_monthly_series_from_manifest() -> None:
    series = build_monthly_series([_manifest_with_observations()])
    assert len(series) == 1
    summary = series[0]
    assert summary.month == "2024-10"
    assert summary.campaign == "2024/25"
    assert summary.satellite_scenes == 1
    assert summary.usable_scenes == 1
    assert summary.ndvi_mean_x1000 == 411
    assert summary.ndvi_max_x1000 == 411
    assert summary.precip_mm_x10 == 0
    assert summary.temp_min_c_x10 == 104
    assert summary.temp_max_c_x10 == 213


def test_build_observations_scales_and_merges_weather() -> None:
    observations = build_observations([_manifest_with_observations()])
    assert observations == [
        {
            "date": "2024-10-02",
            "satellite_usable": True,
            "ndvi_mean_x1000": 411,
            "ndvi_p10_x1000": 171,
            "ndvi_p90_x1000": 740,
            "precip_mm_x10": 0,
            "precip_7d_mm_x10": 0,
            "temp_min_c_x10": 104,
            "temp_max_c_x10": 213,
        }
    ]


def test_build_sources_deduplicates_and_has_no_floats() -> None:
    sources = build_sources([_manifest_with_observations()])
    assert len(sources) == 1
    assert sources[0]["provider"] == "Copernicus CDSE"
    assert sources[0]["retrieved_at"].startswith("2024-10-02T")
