from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from app.blockchain.pdf import render_certification_pdf
from app.blockchain.repository import get_certification_repository
from app.blockchain.schemas import (
    CertificationCreate,
    CertificationDocumentResponse,
    CertificationResponse,
    CertificationVerifyResponse,
)
from app.blockchain.service import (
    build_certification_document,
    build_certification_response,
    get_certification_hero_image,
    issue_certification,
    verify_certification,
)
from app.store import FieldNotFound, get_field_store
from app.timelapse.repository import timelapse_repository

router = APIRouter()
field_store = get_field_store()

CERTIFICATION_HTML_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "certification" / "index.html"
)


def _field_not_found(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "FIELD_NOT_FOUND",
            "message": "The field was not found",
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


def _certification_not_found(
    request: Request, message: str = "Certification not found"
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "CERTIFICATION_NOT_FOUND",
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


def _bad_request(request: Request, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": code,
            "message": message,
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


@router.post(
    "/v1/fields/{field_id}/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a certification snapshot and anchor its hash",
    tags=["Certifications"],
)
def create_certification(
    field_id: UUID, payload: CertificationCreate, request: Request
) -> CertificationResponse:
    try:
        stored_field = field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None

    if payload.period_from > payload.period_to:
        raise _bad_request(
            request, "INVALID_PERIOD", "period_from must be before or equal to period_to"
        )

    datasets = timelapse_repository.list_datasets_for_field(field_id)
    return issue_certification(
        field=stored_field.value,
        datasets=datasets,
        period_from=payload.period_from,
        period_to=payload.period_to,
        anchor=payload.anchor,
    )


@router.get(
    "/v1/fields/{field_id}/certifications",
    response_model=list[CertificationResponse],
    summary="List certification versions for a field",
    tags=["Certifications"],
)
def list_certifications(field_id: UUID, request: Request) -> list[CertificationResponse]:
    try:
        field_store.get(field_id)
    except FieldNotFound:
        raise _field_not_found(request) from None
    return [
        build_certification_response(record)
        for record in get_certification_repository().list_for_field(field_id)
    ]


@router.get(
    "/v1/certifications/{certification_id}",
    response_model=CertificationResponse,
    summary="Get a certification with its anchor details",
    tags=["Certifications"],
)
def get_certification(certification_id: UUID, request: Request) -> CertificationResponse:
    record = get_certification_repository().get(certification_id)
    if record is None:
        raise _certification_not_found(request)
    return build_certification_response(record)


@router.get(
    "/v1/public/certifications/{cert_uid}/verify",
    response_model=CertificationVerifyResponse,
    summary="Verify a certification hash against its on-chain memo",
    tags=["Public fields"],
)
def verify_public_certification(cert_uid: str, request: Request) -> CertificationVerifyResponse:
    result = verify_certification(cert_uid)
    if result is None:
        raise _certification_not_found(request)
    return result


@router.get(
    "/v1/public/certifications/{cert_uid}/hero.png",
    summary="Best usable NDVI frame for a certification document",
    include_in_schema=False,
)
def get_public_certification_hero(cert_uid: str) -> Response:
    image = get_certification_hero_image(cert_uid)
    if image is None:
        raise HTTPException(status_code=404, detail="No hero image available")
    return Response(content=image, media_type="image/png")


@router.get(
    "/v1/public/certifications/{cert_uid}.pdf",
    summary="Download the certification as a print-ready PDF",
    tags=["Public fields"],
)
def get_public_certification_pdf(cert_uid: str, request: Request) -> Response:
    document = build_certification_document(cert_uid)
    if document is None:
        raise _certification_not_found(request)
    return Response(
        content=render_certification_pdf(document),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="certificado-terria-{cert_uid}.pdf"'
        },
    )


@router.get(
    "/v1/public/certifications/{cert_uid}",
    response_model=CertificationDocumentResponse,
    summary="Public certification document: field, snapshot and on-chain anchor",
    tags=["Public fields"],
)
def get_public_certification(
    cert_uid: str, request: Request
) -> CertificationDocumentResponse:
    document = build_certification_document(cert_uid)
    if document is None:
        raise _certification_not_found(request)
    return document


@router.get("/cert/{cert_uid}", response_class=HTMLResponse, include_in_schema=False)
def certification_page(cert_uid: str) -> str:
    if not CERTIFICATION_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Certification page not found")
    return CERTIFICATION_HTML_PATH.read_text(encoding="utf-8")
