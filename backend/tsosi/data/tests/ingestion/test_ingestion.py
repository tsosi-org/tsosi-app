import datetime

import pytest
import tsosi.data.preparation.raw_data_config as dc
from django.core.exceptions import ObjectDoesNotExist
from tsosi.data.ingestion import core
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
    kwargs_base = {
        "data_source_id": "pci",
        "date_data_obtained": datetime.date.today(),
        "full_data": True,
    }

    kwargs_1 = {**kwargs_base, "year": 2020}
    dls_1 = DataLoadSourceFactory.create(**kwargs_1)
    t_1 = TransferFactory.create(data_load_sources=(dls_1,))
    t_2 = TransferFactory.create(data_load_sources=(dls_1,))
    t_3 = TransferFactory.create(data_load_sources=(dls_1,))

    kwargs_2 = {**kwargs_base, "year": 2021}
    dls_2 = DataLoadSourceFactory.create(**kwargs_2)
    t_4 = TransferFactory.create(data_load_sources=(dls_2,))
    t_5 = TransferFactory.create(data_load_sources=(dls_2,))

    test = dc.DataLoadSource(**kwargs_base, data_load_name="test_source")
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

    # Check deletion of old transfers
    for t in [t_1, t_2, t_3, t_4, t_5]:
        with pytest.raises(ObjectDoesNotExist):
            t.refresh_from_db()

        # Ensure entities are not deleted
        t.emitter.refresh_from_db()
        t.recipient
        if t.agents:
            [agent.refresh_from_db() for agent in t.agents.all()]

    # Check deletion of old data loads
    for dls in [dls_1, dls_2]:
        with pytest.raises(ObjectDoesNotExist):
            dls.refresh_from_db()

    # Check "correct" ingestion
    load_sources = DataLoadSource.objects.all()
    assert len(load_sources) == 1

    transfers = Transfer.objects.all()
    assert len(transfers) == 2
    assert transfers[0].recipient.name == transfers[1].recipient.name == "R_1"


@pytest.mark.django_db
def test_ingest_replaced_loads_deduplicate_connected_sources_only(
    datasources, monkeypatch
):
    print(
        "Testing deduplication call on connected sources when replacing loads."
    )

    kwargs_base = {
        "data_source_id": "pci",
        "date_data_obtained": datetime.date.today(),
        "full_data": True,
    }
    old_1 = DataLoadSourceFactory.create(**kwargs_base, year=2020)
    old_2 = DataLoadSourceFactory.create(**kwargs_base, year=2021)

    t_old_1 = TransferFactory.create(data_load_sources=(old_1,))
    t_old_2 = TransferFactory.create(data_load_sources=(old_2,))

    connected_1 = DataLoadSourceFactory.create(
        data_source_id="scipost",
        date_data_obtained=datetime.date.today(),
        full_data=False,
    )
    connected_2 = DataLoadSourceFactory.create(
        data_source_id="operas",
        date_data_obtained=datetime.date.today(),
        full_data=False,
    )

    TransferFactory.create(
        merged_into=t_old_1,
        data_load_sources=(connected_1,),
    )
    TransferFactory.create(
        merged_into=t_old_1,
        data_load_sources=(connected_1,),
    )
    TransferFactory.create(
        merged_into=t_old_2,
        data_load_sources=(connected_2,),
    )

    monkeypatch.setattr(
        core, "ingest_new_records", lambda *args, **kwargs: None
    )

    dedup_called_for = []

    def mock_deduplicate(source):
        dedup_called_for.append(source.pk)
        return 0

    monkeypatch.setattr(core, "deduplicate_transfers", mock_deduplicate)

    new_source = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="replacement_full",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=new_source,
        count=1,
        data=[
            {
                "emitter_name": "E_1",
                "recipient_name": "R_1",
                "date_payment_recipient": "2025-01-01",
                "original_id": "1",
                "amount": 50,
                "currency": "EUR",
                "original_amount_field": "amount",
                "hide_amount": False,
                "raw_data": {},
            }
        ],
    )

    result = ingest(config, send_signals=False)

    assert result is True
    assert set(dedup_called_for) == {connected_1.pk, connected_2.pk}
    assert len(dedup_called_for) == 2


@pytest.mark.django_db
def test_ingest_replaced_loads_without_connected_sources(
    datasources, monkeypatch
):
    print(
        "Testing no deduplication call when replaced loads have no connections."
    )

    old = DataLoadSourceFactory.create(
        data_source_id="pci",
        date_data_obtained=datetime.date.today(),
        full_data=True,
        year=2020,
    )
    TransferFactory.create(data_load_sources=(old,))

    monkeypatch.setattr(
        core, "ingest_new_records", lambda *args, **kwargs: None
    )

    dedup_called_for = []

    def mock_deduplicate(source):
        dedup_called_for.append(source.pk)
        return 0

    monkeypatch.setattr(core, "deduplicate_transfers", mock_deduplicate)

    new_source = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="replacement_full",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=new_source,
        count=1,
        data=[
            {
                "emitter_name": "E_1",
                "recipient_name": "R_1",
                "date_payment_recipient": "2025-01-01",
                "original_id": "1",
                "amount": 50,
                "currency": "EUR",
                "original_amount_field": "amount",
                "hide_amount": False,
                "raw_data": {},
            }
        ],
    )

    result = ingest(config, send_signals=False)

    assert result is True
    assert dedup_called_for == []
