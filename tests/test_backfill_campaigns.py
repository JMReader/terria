from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.timelapse.schemas import TimelapseDatasetSummary
from scripts.backfill_campaigns import parse_campaign
from scripts.seed_monthly_certifications import history_datasets


def _summary(
    *,
    start: date,
    end: date,
    generated_at: datetime,
    status: str = "ready",
    is_demo: bool = False,
) -> TimelapseDatasetSummary:
    return TimelapseDatasetSummary(
        id=uuid4(),
        field_id=UUID("9d103ed2-cfac-4ff9-bd9f-9fa3d9225d38"),
        start_date=start,
        end_date=end,
        status=status,
        is_demo=is_demo,
        generated_at=generated_at,
        frames_count=10,
    )


def test_parse_campaign_maps_to_october_april() -> None:
    assert parse_campaign("2025/26") == (date(2025, 10, 1), date(2026, 4, 30))
    assert parse_campaign("1999/00") == (date(1999, 10, 1), date(2000, 4, 30))
    assert parse_campaign("2024/2025") == (date(2024, 10, 1), date(2025, 4, 30))


def test_parse_campaign_rejects_invalid_values() -> None:
    for value in ["2025", "2025-26", "2025/27", "2025/2024", "abc"]:
        with pytest.raises(Exception):
            parse_campaign(value)


def test_history_datasets_keeps_one_ready_non_demo_per_campaign() -> None:
    older_full = _summary(
        start=date(2024, 10, 1),
        end=date(2025, 4, 30),
        generated_at=datetime(2026, 9, 12, 13, 34, tzinfo=timezone.utc),
    )
    older_cropped = _summary(
        start=date(2024, 10, 1),
        end=date(2025, 4, 30),
        generated_at=datetime(2026, 9, 12, 9, 13, tzinfo=timezone.utc),
    )
    newer = _summary(
        start=date(2025, 10, 1),
        end=date(2026, 4, 30),
        generated_at=datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc),
    )

    class _Repo:
        def list_datasets_for_field(self, _field_id):
            return [newer, older_full, older_cropped]

    history = history_datasets(_Repo(), UUID("9d103ed2-cfac-4ff9-bd9f-9fa3d9225d38"))
    assert [dataset.id for dataset in history] == [older_full.id, newer.id]


def test_history_datasets_ignores_demo_and_not_ready() -> None:
    ready = _summary(
        start=date(2025, 10, 1),
        end=date(2026, 4, 30),
        generated_at=datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc),
    )
    demo = _summary(
        start=date(2025, 10, 1),
        end=date(2026, 4, 30),
        generated_at=datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc),
        is_demo=True,
    )
    pending = _summary(
        start=date(2025, 10, 1),
        end=date(2026, 4, 30),
        generated_at=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
        status="processing",
    )

    class _Repo:
        def list_datasets_for_field(self, _field_id):
            return [pending, demo, ready]

    history = history_datasets(_Repo(), UUID("9d103ed2-cfac-4ff9-bd9f-9fa3d9225d38"))
    assert [dataset.id for dataset in history] == [ready.id]
