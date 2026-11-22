import importlib

import pytest
from django.apps import apps

from tsosi.api.serializers import get_public_raw_data
from tsosi.data.ingestion.transfer_matching import merge_transfers
from tsosi.models import Transfer

from .factories import DataLoadSourceFactory, TransferFactory

migration_0032 = importlib.import_module(
    "tsosi.migrations.0032_remove_transfer_raw_data"
)


@pytest.mark.django_db
def test_empty_merged_raw_data(datasources):
    dls = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin"]
    ]
    merged = merge_transfers(
        TransferFactory.create(data_load_sources=[dls[0]]),
        TransferFactory.create(data_load_sources=[dls[1]]),
    )
    # The former merge stored the sources' raw data by data source
    old_format = {
        s.data_load_sources.first().data_source_id: s.raw_data
        for s in merged.merged_transfers.all()
    }
    Transfer.objects.filter(id=merged.id).update(raw_data=old_format)
    single = TransferFactory.create(data_load_sources=[dls[0]])

    migration_0032.empty_merged_raw_data(apps, None)

    merged.refresh_from_db()
    assert merged.raw_data == {}
    for source in merged.merged_transfers.all():
        assert source.raw_data != {}
    assert Transfer.objects.get(id=single.id).raw_data == single.raw_data


@pytest.mark.django_db
def test_public_raw_data(datasources):
    transfer = TransferFactory.create(
        raw_data={"amount": 1000, "emitter": "E"},
        original_amount_field="amount",
        hide_amount=False,
    )
    assert get_public_raw_data(transfer) == {"amount": 1000, "emitter": "E"}

    # Hidden amount: none of the transfer's entities is a partner showing it
    for entity in [transfer.emitter, transfer.recipient]:
        entity.is_partner = False
        entity.save()
    transfer.agents.clear()
    transfer.hide_amount = True
    assert get_public_raw_data(transfer) == {"emitter": "E"}
    assert transfer.raw_data == {"amount": 1000, "emitter": "E"}
