from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.blockchain.canonical import CanonicalizationError, content_hash
from app.blockchain.payload import build_memo, parse_memo
from app.blockchain.snapshot import (
    build_observations,
    build_sources,
    monthly_up_to,
    observations_up_to,
)
from app.main import app
from app.schemas import PolygonGeometry
from app.timelapse.monthly import build_monthly_series, campaign_of
from app.timelapse.schemas import (
    NdviMetrics,
    TimelapseDatasetSummary,
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
    assert detail.json()["scope"] == "campaign"
    assert detail.json()["month"] is None


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


def test_cumulative_helpers_filter_by_month() -> None:
    observations = [
        {"date": "2024-10-02"},
        {"date": "2024-11-05"},
        {"date": "2024-12-01"},
    ]
    assert [item["date"] for item in observations_up_to(observations, "2024-11")] == [
        "2024-10-02",
        "2024-11-05",
    ]
    monthly = [{"month": "2024-10"}, {"month": "2024-11"}, {"month": "2024-12"}]
    assert monthly_up_to(monthly, "2024-10") == [{"month": "2024-10"}]


def _multi_month_manifest() -> TimelapseManifest:
    frames: list[TimelapseFrame] = []
    weather: list[WeatherDaily] = []
    for index, (year, month_number) in enumerate([(2024, 10), (2024, 11), (2024, 12)]):
        day = date(year, month_number, 10)
        frames.append(
            TimelapseFrame(
                id=uuid4(),
                observed_at=datetime(year, month_number, 10, tzinfo=timezone.utc),
                local_date=day,
                usable=True,
                valid_area_fraction=1.0,
                ndvi=NdviMetrics(mean=0.4 + index / 100, p10=0.17, p90=0.74),
            )
        )
        weather.append(
            WeatherDaily(
                date=day,
                precipitation_mm=5.0,
                precipitation_7d_mm=5.0,
                temperature_min_c=10.0,
                temperature_max_c=20.0,
            )
        )
    return TimelapseManifest(
        dataset_id=uuid4(),
        processing_version="test",
        field_id=uuid4(),
        geometry_version_id=uuid4(),
        boundary=PolygonGeometry(
            type="Polygon", coordinates=[[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.0, 0.0]]]
        ),
        area_hectares=1.0,
        start_date=date(2024, 10, 10),
        end_date=date(2024, 12, 10),
        status="ready",
        generated_at=datetime(2024, 12, 10, tzinfo=timezone.utc),
        frames=frames,
        weather_daily=weather,
        sources=[
            TimelapseSource(
                id="sentinel-2",
                provider="Copernicus CDSE",
                dataset="S2 L2A",
                retrieved_at=datetime(2024, 12, 10, tzinfo=timezone.utc),
                documentation_url="https://example.com",
                attribution="Copernicus",
            )
        ],
    )


def test_monthly_certifications_are_cumulative_and_chained(monkeypatch) -> None:
    from app.blockchain import service
    from app.blockchain.repository import get_certification_repository
    from app.store import get_field_store

    manifest = _multi_month_manifest()
    monkeypatch.setattr(service.timelapse_repository, "get_dataset", lambda _id: manifest)

    field_id = _create_field("Lote Mensual")
    field = get_field_store().get(UUID(field_id)).value
    datasets = [
        TimelapseDatasetSummary(
            id=manifest.dataset_id,
            field_id=field.id,
            start_date=manifest.start_date,
            end_date=manifest.end_date,
            status="ready",
            is_demo=False,
            generated_at=manifest.generated_at,
            frames_count=len(manifest.frames),
        )
    ]

    issued = service.issue_monthly_certifications(field=field, datasets=datasets, anchor=True)
    assert [certification.version for certification in issued] == [1, 2, 3]
    assert issued[0].prev_content_hash is None
    assert issued[1].prev_content_hash == issued[0].content_hash
    assert issued[2].prev_content_hash == issued[1].content_hash
    assert len({certification.content_hash for certification in issued}) == 3
    assert [certification.scope for certification in issued] == ["month", "month", "month"]
    assert [certification.month for certification in issued] == ["2024-10", "2024-11", "2024-12"]

    snapshot = json.loads(get_certification_repository().get_payload(issued[2].id) or b"{}")
    assert snapshot["scope"] == "month"
    assert snapshot["month"] == "2024-12"
    assert snapshot["period"] == {"from": 2024, "to": 2024}
    assert len(snapshot["observations"]) == 3
    assert [item["month"] for item in snapshot["monthly"]] == [
        "2024-10",
        "2024-11",
        "2024-12",
    ]

    verified = client.get(f"/v1/public/certifications/{issued[2].cert_uid}/verify").json()
    assert verified["status"] == "verified"

    again = service.issue_monthly_certifications(field=field, datasets=datasets, anchor=True)
    assert again == []
