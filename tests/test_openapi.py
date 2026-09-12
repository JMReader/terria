from fastapi.testclient import TestClient

from app.main import app


def test_openapi_has_the_field_crud_contract() -> None:
    schema = app.openapi()
    assert schema["openapi"] == "3.1.0"
    assert "/v1/fields" in schema["paths"]
    assert "/v1/public/fields/{public_slug}" in schema["paths"]
    assert "/v1/fields/{field_id}/timelapses" in schema["paths"]
    assert "/v1/timelapse-jobs/{job_id}" in schema["paths"]
    assert "/v1/public/fields/{public_slug}/timelapse" in schema["paths"]
    assert "/v1/fields/{field_id}/certifications" in schema["paths"]
    assert "/v1/certifications/{certification_id}" in schema["paths"]
    assert "/v1/public/certifications/{cert_uid}/verify" in schema["paths"]
    assert "/debug/timelapse" in schema["paths"]
    assert "/v1/fields/{field_id}/simulations/what-if" in schema["paths"]
    assert "/v1/simulations/what-if" in schema["paths"]
    assert "/v1/simulations/what-if/benchmarks" in schema["paths"]
    assert "/v1/simulations/what-if/verify" in schema["paths"]
    assert "/v1/fields/{field_id}/valuations/5yr" in schema["paths"]
    assert "/v1/valuations/5yr" in schema["paths"]
    assert "/v1/valuations/drivers" in schema["paths"]


def _owner_token(client: TestClient, email: str) -> str:
    client.post(
        "/v1/auth/register",
        json={"email": email, "password": "terria1234"},
    )
    login = client.post("/v1/auth/login", json={"email": email, "password": "terria1234"})
    return login.json()["token"]


def test_field_can_be_created_published_and_read_publicly() -> None:
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_owner_token(client, 'tester@terria.dev')}"}
    response = client.post(
        "/v1/fields",
        headers=headers,
        json={
            "name": "La Esperanza",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-64.2, -32.9], [-64.1, -32.9], [-64.1, -32.8], [-64.2, -32.9]]],
            },
        },
    )
    assert response.status_code == 201
    published = client.post(f"/v1/fields/{response.json()['id']}/publish", headers=headers)
    assert published.status_code == 200
    public = client.get(f"/v1/public/fields/{published.json()['public_slug']}")
    assert public.status_code == 200
    assert public.json()["name"] == "La Esperanza"


def test_owner_auth_flow_and_ownership_enforcement() -> None:
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_owner_token(client, 'owner-a@terria.dev')}"}

    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "owner-a@terria.dev"

    created = client.post(
        "/v1/fields",
        headers=headers,
        json={
            "name": "Parcela del owner A",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-63.2, -33.9], [-63.1, -33.9], [-63.1, -33.8], [-63.2, -33.9]]],
            },
        },
    )
    assert created.status_code == 201
    field_id = created.json()["id"]

    mine = client.get("/v1/me/fields", headers=headers)
    assert mine.status_code == 200
    assert any(f["id"] == field_id for f in mine.json())

    # Sin token no se puede publicar
    assert client.post(f"/v1/fields/{field_id}/publish").status_code == 401

    # Otro owner no puede publicar la parcela ajena
    other = _owner_token(client, "owner-b@terria.dev")
    assert (
        client.post(
            f"/v1/fields/{field_id}/publish",
            headers={"Authorization": f"Bearer {other}"},
        ).status_code
        == 403
    )

    # El certificado PDF se genera
    pdf = client.get(f"/v1/fields/{field_id}/certificate.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-1.4")
