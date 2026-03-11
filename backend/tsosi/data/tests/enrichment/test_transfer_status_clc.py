from datetime import UTC, datetime

import pytest
from tsosi.data.enrichment.database_related import update_transfer_status_clc

from ..factories import TransferFactory


@pytest.mark.django_db
def test_transfer_status_clc(datasources, monkeypatch):
    print("Testing the Transfer.is_future boolean update.")

    fixed_now = datetime(2026, 3, 11, 9, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "tsosi.data.enrichment.database_related.timezone.now",
        lambda: fixed_now,
    )

    # Should flip from False to True because date is clearly in the future.
    t_future = TransferFactory.create(
        date_clc={"value": "2999-01-01", "precision": "year"},
        is_future=False,
    )

    # Should flip from True to False because date is clearly in the past.
    t_past = TransferFactory.create(
        date_clc={"value": "1900-01-01", "precision": "year"},
        is_future=True,
    )

    # Day precision: next day should be future.
    t_day_future = TransferFactory.create(
        date_clc={"value": "2026-03-12", "precision": "day"},
        is_future=False,
    )

    # Day precision: previous day should not be future.
    t_day_past = TransferFactory.create(
        date_clc={"value": "2026-03-10", "precision": "day"},
        is_future=True,
    )

    # Equality case: exact same date and precision should not be future.
    t_day_equal = TransferFactory.create(
        date_clc={"value": "2026-03-11", "precision": "day"},
        is_future=True,
    )

    update_transfer_status_clc()

    t_future.refresh_from_db()
    assert t_future.is_future is True

    t_past.refresh_from_db()
    assert t_past.is_future is False

    t_day_future.refresh_from_db()
    assert t_day_future.is_future is True

    t_day_past.refresh_from_db()
    assert t_day_past.is_future is False

    t_day_equal.refresh_from_db()
    assert t_day_equal.is_future is False
