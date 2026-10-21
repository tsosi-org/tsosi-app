import logging

import pytest

from tsosi.data.currencies.currency_rates import compute_transfer_amounts
from tsosi.models import Currency, CurrencyRate

from .factories import TransferFactory

DATE_2024 = {"value": "2024-01-01", "precision": "year"}
# Units of the currency for 1 USD
RATES = {"USD": 1, "EUR": 0.9, "IDR": 16000}


@pytest.fixture
def rates(db):
    for currency, value in RATES.items():
        CurrencyRate.objects.create(
            currency=Currency.objects.get_or_create(id=currency)[0],
            value=value,
            date=DATE_2024,
        )


def eur_transfer(amount: float):
    return TransferFactory.create(
        amount=amount,
        currency_id="EUR",
        date_clc=DATE_2024,
        amounts_clc={"EUR": amount},
    )


@pytest.mark.django_db
def test_compute_transfer_amounts(datasources, rates):
    transfer = eur_transfer(900)
    compute_transfer_amounts()
    transfer.refresh_from_db()
    assert transfer.amounts_clc == {"USD": 1000, "EUR": 900, "IDR": 16000000}


@pytest.mark.django_db
def test_huge_amounts_not_computed(datasources, rates, caplog):
    """
    The converted amounts out of the int64 range are left out, with a
    warning, and the other amounts and transfers are still computed.
    """
    usual = eur_transfer(900)
    # Above int64 in IDR only
    large = eur_transfer(1e16)
    # Above int64 in all the currencies
    huge = eur_transfer(1e19)
    with caplog.at_level(logging.WARNING):
        compute_transfer_amounts()
    usual.refresh_from_db()
    large.refresh_from_db()
    huge.refresh_from_db()
    assert usual.amounts_clc == {"USD": 1000, "EUR": 900, "IDR": 16000000}
    assert large.amounts_clc == {
        "USD": round(1e16 / 0.9),
        "EUR": 10**16,
    }
    assert huge.amounts_clc is None
    assert "Amounts too large in IDR" in caplog.text
    assert str(large.id) in caplog.text
