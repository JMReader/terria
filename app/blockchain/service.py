from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from uuid import UUID, uuid4

from app.blockchain.canonical import canonical_bytes, sha256_hex
from app.blockchain.hero import build_ndvi_preview
from app.blockchain.payload import build_memo, parse_memo
from app.blockchain.provider import explorer_url, get_anchor_provider
from app.blockchain.storage import SupabasePayloadStorage
from app.blockchain.repository import (
    AnchorRecord,
    CertificationRecord,
    get_certification_repository,
)
from app.blockchain.schemas import (
    AnchorResponse,
    CertificationDocumentField,
    CertificationDocumentResponse,
    CertificationResponse,
    CertificationVerifyResponse,
)
from app.blockchain.snapshot import build_observations, build_snapshot, build_sources
from app.config import settings
from app.schemas import FieldResponse
from app.store import FieldNotFound, get_field_store
from app.timelapse.monthly import build_monthly_series
from app.timelapse.repository import timelapse_repository
from app.timelapse.schemas import TimelapseDatasetSummary

logger = logging.getLogger(__name__)


def _repo():
    """SQLite local o Supabase segun la configuracion activa."""
    return get_certification_repository()


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
    anchor = _repo().get_anchor(record.id)
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
    version = _repo().next_version(field.id)
    prev_hash = _repo().previous_content_hash(field.id)

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
        monthly=[summary.model_dump() for summary in build_monthly_series(manifests)],
        sources=build_sources(manifests),
    )
    payload = canonical_bytes(snapshot)
    content_hash_hex = sha256_hex(payload)

    record = _repo().create_certification(
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
    _repo().save_payload(record.id, payload, content_hash_hex)

    if not anchor:
        return build_certification_response(record)

    memo = build_memo(cert_uid, content_hash_hex, prev_hash)
    provider = get_anchor_provider()
    try:
        result = provider.anchor(memo)
    except Exception as exc:  # noqa: BLE001 - anchoring must never lose the snapshot
        message = str(exc)[:500]
        _repo().save_anchor(
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
        _repo().enqueue_anchor_job(record.id, message)
        record = _repo().set_status(record.id, "pending_anchor")
        return build_certification_response(record)

    _repo().save_anchor(
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
    record = _repo().set_status(
        record.id, "anchored", issued_at=datetime.now(timezone.utc)
    )
    return build_certification_response(record)


def verify_certification(cert_uid: str) -> CertificationVerifyResponse | None:
    record = _repo().get_by_cert_uid(cert_uid)
    if record is None:
        return None

    payload = _repo().get_payload(record.id)
    recomputed = sha256_hex(payload) if payload is not None else ""
    anchor = _repo().get_anchor(record.id)

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


def _document_field(
    field_id: UUID, snapshot: dict
) -> CertificationDocumentField:
    try:
        field = get_field_store().get(field_id).value
        return CertificationDocumentField(
            id=field.id,
            name=field.name,
            description=field.description,
            locality=field.locality,
            province=field.province,
            area_hectares=field.area_hectares,
            boundary=field.boundary,
        )
    except FieldNotFound:
        field_meta = snapshot.get("field", {}) if isinstance(snapshot, dict) else {}
        return CertificationDocumentField(
            id=field_id,
            name=field_meta.get("name") or f"Campo {str(field_id)[:8]}",
            area_hectares=float(field_meta.get("area_ha") or 0.0),
            province=field_meta.get("province"),
        )


def build_certification_document(cert_uid: str) -> CertificationDocumentResponse | None:
    """Ficha pública completa del certificado: campo + snapshot + ancla on-chain."""
    record = _repo().get_by_cert_uid(cert_uid)
    if record is None:
        return None

    payload = _repo().get_payload(record.id)
    snapshot: dict = {}
    if payload is not None:
        try:
            snapshot = json.loads(payload)
        except (ValueError, TypeError):
            snapshot = {}

    anchor = _repo().get_anchor(record.id)
    verification = verify_certification(cert_uid)

    return CertificationDocumentResponse(
        cert_uid=record.cert_uid,
        version=record.version,
        status=record.status,  # type: ignore[arg-type]
        schema_version=record.schema_version,
        algorithm_version=record.algorithm_version,
        period_from=record.period_from,
        period_to=record.period_to,
        content_hash=record.content_hash or "",
        prev_content_hash=record.prev_content_hash,
        issued_at=record.issued_at,
        created_at=record.created_at,
        verification_status=verification.status if verification else "pending",
        field=_document_field(record.field_id, snapshot),
        anchor=_anchor_response(anchor),
        snapshot=snapshot,
        hero_image_url=f"/v1/public/certifications/{record.cert_uid}/hero.png",
    )


def _local_hero_image(snapshot: dict) -> bytes | None:
    """PNG NDVI ya generado en disco por el worker de timelapse."""
    for dataset in snapshot.get("datasets", []):
        try:
            manifest = timelapse_repository.get_dataset(UUID(str(dataset.get("id"))))
        except (ValueError, TypeError):
            continue
        if manifest is None:
            continue
        usable = [frame for frame in manifest.frames if frame.usable and frame.ndvi.mean is not None]
        if not usable:
            continue
        best = max(usable, key=lambda frame: frame.ndvi.mean or 0.0)
        path = settings.assets_dir / f"{best.id}_ndvi.png"
        if path.exists():
            return path.read_bytes()
    return None


def _asset_storage() -> SupabasePayloadStorage | None:
    if not (settings.supabase_url and settings.supabase_service_role_key):
        return None
    try:
        return SupabasePayloadStorage(bucket=settings.assets_storage_bucket)
    except RuntimeError:
        return None


def _generate_hero_image(field_id: UUID, snapshot: dict) -> bytes | None:
    try:
        field = get_field_store().get(field_id).value
    except FieldNotFound:
        return None

    datasets = snapshot.get("datasets", [])
    if datasets and datasets[0].get("start") and datasets[0].get("end"):
        start_date, end_date = datasets[0]["start"], datasets[0]["end"]
    else:
        period = snapshot.get("period", {})
        if not (period.get("from") and period.get("to")):
            return None
        start_date, end_date = f"{period['from']}-10-01", f"{period['to']}-04-30"
    return build_ndvi_preview(field.boundary, start_date, end_date)


def get_certification_hero_image(cert_uid: str) -> bytes | None:
    """PNG NDVI del certificado: disco local → Supabase Storage → generado y cacheado.

    El PNG es ilustrativo (no forma parte del hash del snapshot). Se genera con
    Sentinel-2 vía Planetary Computer, sin cuenta Copernicus.
    """
    record = _repo().get_by_cert_uid(cert_uid)
    if record is None:
        return None
    payload = _repo().get_payload(record.id)
    if payload is None:
        return None
    try:
        snapshot = json.loads(payload)
    except (ValueError, TypeError):
        return None

    local = _local_hero_image(snapshot)
    if local is not None:
        return local

    storage = _asset_storage()
    storage_ref = f"{settings.assets_storage_bucket}/certificates/{cert_uid}.png"
    if storage is not None:
        try:
            cached = storage.download(storage_ref)
        except Exception:  # noqa: BLE001 - a storage outage must not break the certificate
            cached = None
        if cached is not None:
            return cached

    if not settings.cert_hero_generate:
        return None

    generated = _generate_hero_image(record.field_id, snapshot)
    if generated is not None and storage is not None:
        try:
            storage.upload(f"certificates/{cert_uid}.png", generated, "image/png")
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            logger.warning("Could not cache hero image for %s: %s", cert_uid, exc)
    return generated
