from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas import PolygonGeometry, StrictModel

CertificationStatus = Literal["draft", "pending_anchor", "anchored", "failed", "superseded"]
AnchorStatus = Literal["pending", "confirmed", "failed"]
VerifyStatus = Literal["verified", "tampered", "pending", "rpc_unavailable"]


class CertificationCreate(StrictModel):
    period_from: Annotated[int, Field(ge=2000, le=2100)]
    period_to: Annotated[int, Field(ge=2000, le=2100)]
    anchor: bool = True


class AnchorResponse(StrictModel):
    provider: str
    cluster: str
    memo_payload: str
    tx_signature: str | None
    slot: int | None
    block_time: datetime | None
    status: AnchorStatus
    explorer_url: str | None


class CertificationResponse(StrictModel):
    id: UUID
    field_id: UUID
    version: int
    cert_uid: str
    schema_version: str
    algorithm_version: str
    period_from: int
    period_to: int
    status: CertificationStatus
    content_hash: str
    prev_content_hash: str | None
    issued_at: datetime | None
    created_at: datetime
    anchor: AnchorResponse | None = None


class CertificationVerifyResponse(StrictModel):
    status: VerifyStatus
    cert_uid: str
    field_id: UUID
    version: int
    expected_hash: str
    recomputed_hash: str
    on_chain_memo: str | None
    tx_signature: str | None
    explorer_url: str | None


class CertificationDocumentField(StrictModel):
    id: UUID
    name: str
    description: str | None = None
    locality: str | None = None
    province: str | None = None
    area_hectares: float
    boundary: PolygonGeometry | None = None


class CertificationDocumentResponse(StrictModel):
    """Documento completo para renderizar el certificado (ficha pública)."""

    cert_uid: str
    version: int
    status: CertificationStatus
    schema_version: str
    algorithm_version: str
    period_from: int
    period_to: int
    content_hash: str
    prev_content_hash: str | None
    issued_at: datetime | None
    created_at: datetime
    verification_status: VerifyStatus
    field: CertificationDocumentField
    anchor: AnchorResponse | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    hero_image_url: str | None = None
