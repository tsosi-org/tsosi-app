import datetime

import pytest
from django.core.cache import cache
from django.test import Client

from .factories import DataLoadSourceFactory, TransferFactory


@pytest.mark.django_db
def test_home_figures(datasources):
    cache.clear()
    # Every transfer gets one of these data loads: the factory's default one
    # has a random date, that could be the latest.
    dls_old = DataLoadSourceFactory.create(
        date_data_obtained=datetime.date(2025, 1, 10)
    )
    dls_new = DataLoadSourceFactory.create(
        date_data_obtained=datetime.date(2026, 3, 2)
    )
    TransferFactory.create(
        amounts_clc={"USD": 1000.4, "EUR": 900}, data_load_sources=[dls_old]
    )
    kept = TransferFactory.create(
        amounts_clc={"USD": 500.3, "EUR": 450}, data_load_sources=[dls_new]
    )
    # A support without amount is counted, with no amount
    no_amount = TransferFactory.create(data_load_sources=[dls_old])
    no_amount.amounts_clc = None
    no_amount.save()
    # Merged and future transfers are left out
    TransferFactory.create(
        amounts_clc={"USD": 10_000},
        merged_into=kept,
        data_load_sources=[dls_old],
    )
    TransferFactory.create(
        amounts_clc={"USD": 10_000},
        is_future=True,
        data_load_sources=[dls_old],
    )

    response = Client().get("/api/home-figures")

    assert response.status_code == 200
    assert response.json() == {
        "supports": 3,
        "amount_usd": 1501,
        "date_data_update": "2026-03-02",
    }
