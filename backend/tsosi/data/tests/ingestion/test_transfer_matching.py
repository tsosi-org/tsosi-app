from datetime import datetime

import pytest
from tsosi.data.exceptions import DataException
from tsosi.data.ingestion.core import ingest
from tsosi.data.ingestion.transfer_matching import deduplicate_transfers
from tsosi.data.preparation.raw_data_config import DataIngestionConfig
from tsosi.models import DataLoadSource, Transfer

from ..factories import DataLoadSourceFactory, TransferFactory


@pytest.mark.django_db
def test_deduplicate_transferss(datasources):
    dls = DataLoadSourceFactory.create(data_source_id="uga")
    transfers = TransferFactory.create_batch(2, data_load_sources=(dls,))
    transfer = transfers[0]
    dls = DataLoadSourceFactory.create(data_source_id="pci")
    TransferFactory.create(
        data_load_sources=(dls,),
        emitter_id=transfer.emitter_id,
        agent_id=transfer.agent_id,
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
        agent_id=transfer.agent_id,
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
        agent_id=transfer.agent_id,
        recipient_id=transfer.recipient_id,
        amount=transfer.amount,
        currency=transfer.currency,
        date_invoice=transfer.date_invoice,
        date_payment_emitter=transfer.date_payment_emitter,
        date_payment_recipient=transfer.date_payment_recipient,
    )
    with pytest.raises(DataException):
        deduplicate_transfers(dls)
