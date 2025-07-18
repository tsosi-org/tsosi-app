import datetime

import pytest
import tsosi.data.preparation.raw_data_config as dc
from django.core.exceptions import ObjectDoesNotExist
from tsosi.data.ingestion.core import ingest
from tsosi.models import DataLoadSource, Transfer
from tsosi.tasks import ingest_test

from ..factories import DataLoadSourceFactory, TransferFactory


@pytest.mark.django_db
def test_ingest_test_data(registries):
    print("Testing test data ingestion.")
    ingest_test()


@pytest.mark.django_db
def test_old_data_load_deletion(datasources):
    print("Testing the deletion of old data loads.")
    kwargs = {
        "data_source_id": "pci",
        "data_load_name": "test_load",
        "date_data_obtained": datetime.date.today(),
        "full_data": True,
    }
    dls = DataLoadSourceFactory.create(**kwargs)
    t_1 = TransferFactory.create(data_load_source=dls)
    t_2 = TransferFactory.create(data_load_source=dls)
    t_3 = TransferFactory.create(data_load_source=dls)

    test = dc.DataLoadSource(**kwargs)
    test_data = [
        {
            "emitter_name": "E_1",
            "date_payment_recipient": "2025-01-01",
            "recipient_name": "R_1",
            "original_id": "1",
            "amount": 50,
            "currency": "EUR",
            "original_amount_field": "amount",
            "hide_amount": False,
            "raw_data": {},
        },
        {
            "emitter_name": "E_2",
            "recipient_name": "R_1",
            "date_payment_recipient": "2025-01-01",
            "original_id": "2",
            "amount": 50,
            "currency": "EUR",
            "original_amount_field": "amount",
            "hide_amount": False,
            "raw_data": {},
        },
    ]

    data_ingestion_config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=test,
        count=len(test_data),
        data=test_data,
    )

    ingest(data_ingestion_config, send_signals=False)

    for t in [t_1, t_2, t_3]:
        with pytest.raises(ObjectDoesNotExist):
            Transfer.objects.get(pk=t.pk)

    with pytest.raises(ObjectDoesNotExist):
        DataLoadSource.objects.get(pk=dls.pk)

    load_sources = DataLoadSource.objects.all()
    assert len(load_sources) == 1

    transfers = Transfer.objects.all()
    assert len(transfers) == 2
    assert transfers[0].recipient.name == transfers[1].recipient.name == "R_1"
