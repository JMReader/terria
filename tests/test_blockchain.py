from __future__ import annotations

from fastapi.testclient import TestClient

from app.blockchain.canonical import CanonicalizationError, content_hash
from app.blockchain.payload import build_memo, parse_memo
from app.main import app

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


def test_verify_unknown_certification_returns_404() -> None:
    response = client.get("/v1/public/certifications/does-not-exist/verify")
    assert response.status_code == 404


def test_invalid_period_is_rejected() -> None:
    field_id = _create_field("Lote Período")
    response = client.post(
        f"/v1/fields/{field_id}/certifications",
        json={"period_from": 2026, "period_to": 2018},
    )
    assert response.status_code == 422
