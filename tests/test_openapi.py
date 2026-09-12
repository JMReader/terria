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


def test_field_can_be_created_published_and_read_publicly() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/fields",
        json={
            "name": "La Esperanza",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[-64.2, -32.9], [-64.1, -32.9], [-64.1, -32.8], [-64.2, -32.9]]],
            },
        },
    )
    assert response.status_code == 201
    published = client.post(f"/v1/fields/{response.json()['id']}/publish")
    assert published.status_code == 200
    public = client.get(f"/v1/public/fields/{published.json()['public_slug']}")
    assert public.status_code == 200
    assert public.json()["name"] == "La Esperanza"
