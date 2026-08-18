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
    right_transfer = merge_transfers(*transfers)
    left_transfer = TransferFactory.create(
        data_load_sources=[data_load_sources[2]]
    )
    merged_transfer = merge_transfers(left_transfer, right_transfer)
    for transfer in transfers:
        transfer.refresh_from_db()
    assert right_transfer.id is None
    assert all(
        [transfer.merged_into == merged_transfer for transfer in transfers]
    )
    assert merged_transfer.data_load_sources.count() == 3
    assert len(merged_transfer.raw_data) == 3


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
