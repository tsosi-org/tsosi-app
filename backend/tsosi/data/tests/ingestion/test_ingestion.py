import datetime

import pytest
from django.core.exceptions import ObjectDoesNotExist

import tsosi.data.preparation.raw_data_config as dc
from tsosi.data.ingestion import core
from tsosi.data.ingestion.core import ingest
from tsosi.models import DataLoadSource, Entity, Transfer
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK
from tsosi.tasks import ingest_test

from ..factories import DataLoadSourceFactory, EntityFactory, TransferFactory


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
            "hide_amount": False,
        },
        {
            "emitter_name": "E_2",
            "recipient_name": "R_1",
            "date_payment_recipient": "2025-01-01",
            "original_id": "2",
            "amount": 50,
            "currency": "EUR",
            "hide_amount": False,
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
def test_ingest_existing_entities_does_not_create_new_entities(
    datasources, monkeypatch
):
    print("Testing ingestion when all entities already exist.")

    monkeypatch.setattr(core, "fill_static_data", lambda: None)

    emitter = EntityFactory.create(name="E_1")
    recipient = EntityFactory.create(name="R_1")
    initial_entity_count = Entity.objects.count()
    initial_transfer_count = Transfer.objects.count()

    source = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="existing_entities",
        date_data_obtained=datetime.date.today(),
        full_data=False,
    )
    config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=source,
        count=1,
        data=[
            {
                "emitter_name": emitter.name,
                "emitter_country": emitter.country,
                "recipient_name": recipient.name,
                "recipient_country": recipient.country,
                "date_payment_recipient": "2025-01-01",
                "original_id": "1",
                "amount": 50,
                "currency": "EUR",
                "hide_amount": False,
            }
        ],
    )

    result = ingest(config, send_signals=False)

    assert result is True
    assert Entity.objects.count() == initial_entity_count
    assert Transfer.objects.count() == initial_transfer_count + 1
    transfer = Transfer.objects.latest("date_created")
    assert transfer.emitter_id == emitter.id
    assert transfer.recipient_id == recipient.id


@pytest.mark.django_db
def test_ingest_scope_and_history(registries, datasources, monkeypatch):
    print("Testing the scope and history of ingested data.")

    monkeypatch.setattr(core, "fill_static_data", lambda: None)

    to_check = EntityFactory.create(name="R_2", scope=ENTITY_SCOPE_TO_CHECK)
    source = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="scope",
        date_data_obtained=datetime.date.today(),
        full_data=False,
    )
    data = [
        {
            "emitter_name": "E_1",
            "recipient_name": recipient_name,
            "date_payment_recipient": "2025-01-01",
            "original_id": str(i),
            "amount": 50,
            "currency": "EUR",
            "hide_amount": False,
        }
        for i, recipient_name in enumerate(["R_1", to_check.name])
    ]
    config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=source,
        count=len(data),
        data=data,
    )

    ingest(config, send_signals=False)

    # New beneficiaries are in scope, the curation board's decisions are kept
    assert Entity.objects.get(name="R_1").scope == ENTITY_SCOPE_IN
    assert Entity.objects.get(name="E_1").scope is None
    to_check.refresh_from_db()
    assert to_check.scope == ENTITY_SCOPE_TO_CHECK

    # The bulk created records are in the history
    for transfer in Transfer.objects.all():
        assert transfer.history.filter(history_type="+").exists()
    for entity in Entity.objects.filter(name__in=["E_1", "R_1"]):
        assert entity.history.filter(history_type="+").exists()


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
                "hide_amount": False,
            }
        ],
    )

    result = ingest(config, send_signals=False)

    assert result is True
    assert dedup_called_for == []
