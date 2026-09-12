from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.blockchain.canonical import canonical_bytes, sha256_hex
from app.blockchain.payload import build_memo, parse_memo
from app.blockchain.provider import explorer_url, get_anchor_provider
from app.blockchain.repository import (
    AnchorRecord,
    CertificationRecord,
    certification_repository,
)
from app.blockchain.schemas import (
    AnchorResponse,
    CertificationResponse,
    CertificationVerifyResponse,
)
from app.blockchain.snapshot import build_observations, build_snapshot, build_sources
from app.config import settings
from app.schemas import FieldResponse
from app.timelapse.repository import timelapse_repository
from app.timelapse.schemas import TimelapseDatasetSummary


def _anchor_response(anchor: AnchorRecord | None) -> AnchorResponse | None:
    if anchor is None:
        return None
    return AnchorResponse(
        provider=anchor.provider,
        cluster=anchor.cluster,
        memo_payload=anchor.memo_payload,
        tx_signature=anchor.tx_signature,
        slot=anchor.slot,
        block_time=anchor.block_time,
        status=anchor.status,  # type: ignore[arg-type]
        explorer_url=explorer_url(anchor.cluster, anchor.tx_signature),
    )


def build_certification_response(record: CertificationRecord) -> CertificationResponse:
    anchor = certification_repository.get_anchor(record.id)
    return CertificationResponse(
        id=record.id,
        field_id=record.field_id,
        version=record.version,
        cert_uid=record.cert_uid,
        schema_version=record.schema_version,
        algorithm_version=record.algorithm_version,
        period_from=record.period_from,
        period_to=record.period_to,
        status=record.status,  # type: ignore[arg-type]
        content_hash=record.content_hash or "",
        prev_content_hash=record.prev_content_hash,
        issued_at=record.issued_at,
        created_at=record.created_at,
        anchor=_anchor_response(anchor),
    )


def issue_certification(
    *,
    field: FieldResponse,
    datasets: list[TimelapseDatasetSummary],
    period_from: int,
    period_to: int,
    anchor: bool = True,
) -> CertificationResponse:
    cert_uid = str(uuid4())
    version = certification_repository.next_version(field.id)
    prev_hash = certification_repository.previous_content_hash(field.id)

    manifests = [
        manifest
        for dataset in datasets
        if (manifest := timelapse_repository.get_dataset(dataset.id)) is not None
    ]

    snapshot = build_snapshot(
        field=field,
        datasets=datasets,
        period_from=period_from,
        period_to=period_to,
        cert_uid=cert_uid,
        schema_version=settings.cert_schema_version,
        prev_hash=prev_hash,
        observations=build_observations(manifests),
        sources=build_sources(manifests),
    )
    payload = canonical_bytes(snapshot)
    content_hash_hex = sha256_hex(payload)

    record = certification_repository.create_certification(
        field_id=field.id,
        version=version,
        cert_uid=cert_uid,
        schema_version=settings.cert_schema_version,
        algorithm_version=settings.cert_algorithm_version,
        period_from=period_from,
        period_to=period_to,
        status="draft",
        content_hash=content_hash_hex,
        prev_content_hash=prev_hash,
        issued_at=None,
    )
    certification_repository.save_payload(record.id, payload, content_hash_hex)

    if not anchor:
        return build_certification_response(record)

    memo = build_memo(cert_uid, content_hash_hex, prev_hash)
    provider = get_anchor_provider()
    try:
        result = provider.anchor(memo)
    except Exception as exc:  # noqa: BLE001 - anchoring must never lose the snapshot
        message = str(exc)[:500]
        certification_repository.save_anchor(
            certification_id=record.id,
            provider=provider.name,
            cluster=provider.cluster,
            memo_payload=memo,
            tx_signature=None,
            slot=None,
            block_time=None,
            status="failed",
            attempts=1,
            error=message,
        )
        certification_repository.enqueue_anchor_job(record.id, message)
        record = certification_repository.set_status(record.id, "pending_anchor")
        return build_certification_response(record)

    certification_repository.save_anchor(
        certification_id=record.id,
        provider=result.provider,
        cluster=result.cluster,
        memo_payload=result.memo,
        tx_signature=result.tx_signature,
        slot=result.slot,
        block_time=result.block_time,
        status="confirmed",
        attempts=1,
        error=None,
    )
    record = certification_repository.set_status(
        record.id, "anchored", issued_at=datetime.now(timezone.utc)
    )
    return build_certification_response(record)


def verify_certification(cert_uid: str) -> CertificationVerifyResponse | None:
    record = certification_repository.get_by_cert_uid(cert_uid)
    if record is None:
        return None

    payload = certification_repository.get_payload(record.id)
    recomputed = sha256_hex(payload) if payload is not None else ""
    anchor = certification_repository.get_anchor(record.id)

    status: str = "pending"
    on_chain_memo: str | None = None
    tx_signature = anchor.tx_signature if anchor else None

    if payload is not None and anchor is not None and anchor.status == "confirmed":
        if anchor.cluster == "local":
            on_chain_memo = anchor.memo_payload
            parsed = parse_memo(on_chain_memo)
            matches = parsed["content_hash"] == recomputed == record.content_hash
            status = "verified" if matches else "tampered"
        else:
            provider = get_anchor_provider()
            try:
                on_chain_memo = provider.fetch_memo(anchor.tx_signature or "")
            except Exception:  # noqa: BLE001 - RPC outages should not raise
                on_chain_memo = None
            if on_chain_memo is None:
                status = "rpc_unavailable"
            else:
                parsed = parse_memo(on_chain_memo)
                matches = parsed["content_hash"] == recomputed == record.content_hash
                status = "verified" if matches else "tampered"

    return CertificationVerifyResponse(
        status=status,  # type: ignore[arg-type]
        cert_uid=record.cert_uid,
        field_id=record.field_id,
        version=record.version,
        expected_hash=record.content_hash or "",
        recomputed_hash=recomputed,
        on_chain_memo=on_chain_memo,
        tx_signature=tx_signature,
        explorer_url=explorer_url(anchor.cluster, tx_signature) if anchor else None,
    )
