import pytest

from tsosi.data.exceptions import DataException
from tsosi.data.ingestion.transfer_matching import (
    deduplicate_transfers,
    merge_transfers,
)
from tsosi.models import Transfer

from ..factories import DataLoadSourceFactory, TransferFactory


@pytest.mark.django_db
def test_merge_transfers(datasources):
    data_load_sources = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin", "doaj"]
    ]
    transfers = [
        TransferFactory.create(data_load_sources=[dls])
        for dls in data_load_sources[:2]
    ]
    public_id = transfers[1].id
    right_transfer = merge_transfers(*transfers)
    assert right_transfer.id == public_id
    left_transfer = TransferFactory.create(
        data_load_sources=[data_load_sources[2]]
    )
    merged_transfer = merge_transfers(left_transfer, right_transfer)
    assert merged_transfer.id == public_id
    assert merged_transfer.merged_into is None
    sources = merged_transfer.merged_transfers.all()
    assert sources.count() == 3
    assert not any(source.merged_transfers.exists() for source in sources)
    assert merged_transfer.data_load_sources.count() == 3
    assert Transfer.objects.filter(merged_into__isnull=True).count() == 1


@pytest.mark.django_db
def test_merge_transfers_history(datasources):
    dls = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin", "doaj"]
    ]
    left = merge_transfers(
        TransferFactory.create(data_load_sources=[dls[0]], amount=100),
        TransferFactory.create(data_load_sources=[dls[1]], amount=100),
    )
    left_id = left.id
    right = TransferFactory.create(data_load_sources=[dls[2]], amount=200)
    merged = merge_transfers(left, right)
    # The merged transfer's previous values and the deletion of the left
    # merged transfer are kept in the history
    assert merged.history.filter(amount=200).exists()
    assert merged.history.latest().amount == 100
    assert Transfer.history.filter(id=left_id, history_type="-").exists()


@pytest.mark.django_db
def test_merge_transfers_keeps_right_source_values(datasources):
    dls_left, dls_right = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin"]
    ]
    left = TransferFactory.create(data_load_sources=[dls_left], amount=100)
    right = TransferFactory.create(data_load_sources=[dls_right], amount=200)
    right_original_id = right.original_id
    right_agents = set(right.agents.all())
    merged = merge_transfers(left, right)
    right_source = merged.merged_transfers.get(data_load_sources=dls_right)
    assert right_source.id != merged.id
    assert right_source.amount == 200
    assert right_source.original_id == str(right_original_id)
    assert set(right_source.agents.all()) == right_agents


@pytest.mark.django_db
def test_merge_transfers_left_merged(datasources):
    dls = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin", "doaj"]
    ]
    left = merge_transfers(
        TransferFactory.create(data_load_sources=[dls[0]]),
        TransferFactory.create(data_load_sources=[dls[1]]),
    )
    left_id = left.id
    right = TransferFactory.create(data_load_sources=[dls[2]])
    merged = merge_transfers(left, right)
    assert merged.id == right.id
    assert merged.merged_transfers.count() == 3
    assert not Transfer.objects.filter(id=left_id).exists()
    assert Transfer.objects.filter(merged_into__isnull=True).count() == 1


@pytest.mark.django_db
def test_merge_transfers_keeps_best_values(datasources):
    dls_left, dls_right = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin"]
    ]
    left = TransferFactory.create(
        data_load_sources=[dls_left],
        amount=100,
        date_invoice={"value": "2024-01-01", "precision": "year"},
    )
    right = TransferFactory.create(
        data_load_sources=[dls_right],
        amount=200,
        date_invoice={"value": "2024-03-15", "precision": "day"},
    )
    merged = merge_transfers(left, right)
    assert merged.amount == 100
    assert merged.date_invoice == right.date_invoice


@pytest.mark.django_db
def test_merge_transfers_resets_computed_fields(datasources):
    dls_left, dls_right = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin"]
    ]
    left = TransferFactory.create(data_load_sources=[dls_left])
    right = TransferFactory.create(data_load_sources=[dls_right])
    assert right.amounts_clc is not None
    merged = merge_transfers(left, right)
    merged.refresh_from_db()
    assert merged.amounts_clc is None
    assert merged.date_clc is None


@pytest.mark.django_db
def test_deduplicate_transferss(datasources):
    dls = DataLoadSourceFactory.create(data_source_id="uga")
    transfers = TransferFactory.create_batch(2, data_load_sources=(dls,))
    transfer = transfers[0]
    dls = DataLoadSourceFactory.create(data_source_id="pci")
    TransferFactory.create(
        data_load_sources=(dls,),
        emitter_id=transfer.emitter_id,
        agents=transfer.agents.all(),
        recipient_id=transfer.recipient_id,
        amount=transfer.amount,
        currency=transfer.currency,
        date_invoice=transfer.date_invoice,
        date_payment_emitter=transfer.date_payment_emitter,
        date_payment_recipient=transfer.date_payment_recipient,
    )
    deduplicate_transfers(dls)

    assert Transfer.objects.count() == 4
    assert Transfer.objects.filter(merged_into__isnull=True).count() == 2


@pytest.mark.django_db
def test_deduplicate_transfers_multiple_match(datasources):
    dls = DataLoadSourceFactory.create(data_source_id="uga")
    transfers = TransferFactory.create_batch(1, data_load_sources=(dls,))
    transfer = transfers[0]
    dls = DataLoadSourceFactory.create(data_source_id="pci")
    TransferFactory.create(
        data_load_sources=(dls,),
        emitter_id=transfer.emitter_id,
        agents=transfer.agents.all(),
        recipient_id=transfer.recipient_id,
        amount=transfer.amount,
        currency=transfer.currency,
        date_invoice=transfer.date_invoice,
        date_payment_emitter=transfer.date_payment_emitter,
        date_payment_recipient=transfer.date_payment_recipient,
    )
    TransferFactory.create(
        data_load_sources=(dls,),
        emitter_id=transfer.emitter_id,
        agents=transfer.agents.all(),
        recipient_id=transfer.recipient_id,
        amount=transfer.amount,
        currency=transfer.currency,
        date_invoice=transfer.date_invoice,
        date_payment_emitter=transfer.date_payment_emitter,
        date_payment_recipient=transfer.date_payment_recipient,
    )
    with pytest.raises(DataException):
        deduplicate_transfers(dls)
