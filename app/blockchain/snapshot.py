from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas import FieldResponse
from app.timelapse.schemas import TimelapseDatasetSummary


def decimal_str(value: float, places: int = 2) -> str:
    """Floats break canonical hashing, so numbers travel as fixed decimal strings."""
    return f"{value:.{places}f}"


def build_snapshot(
    *,
    field: FieldResponse,
    datasets: list[TimelapseDatasetSummary],
    period_from: int,
    period_to: int,
    cert_uid: str,
    schema_version: str,
    prev_hash: str | None,
    issued_at: datetime | None = None,
) -> dict[str, Any]:
    issued = (issued_at or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    return {
        "schema_version": schema_version,
        "cert_uid": cert_uid,
        "field": {
            "uid": str(field.id),
            "area_ha": decimal_str(field.area_hectares),
            "province": field.province,
        },
        "period": {"from": period_from, "to": period_to},
        "datasets": [
            {
                "id": str(dataset.id),
                "start": dataset.start_date.isoformat(),
                "end": dataset.end_date.isoformat(),
                "status": dataset.status,
                "frames": dataset.frames_count,
                "is_demo": bool(dataset.is_demo),
            }
            for dataset in datasets
        ],
        "issued_at": issued,
        "prev_snapshot_hash": prev_hash,
    }
