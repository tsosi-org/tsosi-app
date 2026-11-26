import pytest

from tsosi.data.exceptions import DataException
from tsosi.data.ingestion.transfer_matching import (
    CRITERIA_DATE_CLC,
    deduplicate_transfers,
    merge_transfers,
    transfer_is_matching,
)
from tsosi.models import Transfer
from tsosi.models.static_data import HUB_DATA_SOURCE

from ..factories import DataLoadSourceFactory, EntityFactory, TransferFactory


@pytest.mark.django_db
def test_merge_transfers(db):
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
def test_merge_transfers_history(db):
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
def test_merge_transfers_keeps_right_source_values(db):
    dls_left, dls_right = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", "couperin"]
    ]
    left = TransferFactory.create(data_load_sources=[dls_left], amount=100)
    right = TransferFactory.create(data_load_sources=[dls_right], amount=200)
    right_original_id = right.original_id
    right_agents = set(right.agents.all())
    right_raw_data = right.raw_data
    merged = merge_transfers(left, right)
    right_source = merged.merged_transfers.get(data_load_sources=dls_right)
    assert right_source.id != merged.id
    assert right_source.amount == 200
    assert right_source.original_id == str(right_original_id)
    assert set(right_source.agents.all()) == right_agents
    # The raw data is kept in the source transfers only
    assert right_source.raw_data == right_raw_data != {}
    assert right_source.original_amount_field == "amount"
    assert merged.raw_data == {}
    assert merged.original_amount_field == ""


@pytest.mark.django_db
def test_merge_transfers_left_merged(db):
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
def test_merge_transfers_keeps_best_values(db):
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
def test_merge_transfers_hub_precedence(db):
    """The values declared in the Hub win over the best value rule."""
    dls_left, dls_hub = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", HUB_DATA_SOURCE]
    ]
    left = TransferFactory.create(
        data_load_sources=[dls_left],
        amount=100,
        date_invoice={"value": "2024-03-15", "precision": "day"},
        agents=[EntityFactory.create()],
    )
    hub = TransferFactory.create(
        data_load_sources=[dls_hub],
        amount=200,
        date_invoice={"value": "2024-01-01", "precision": "year"},
        date_payment_emitter=None,
        hub_values=True,
    )
    merged = merge_transfers(left, hub)
    assert merged.amount == 200
    assert merged.date_invoice == hub.date_invoice
    assert not merged.agents.exists()
    # The dates it doesn't declare come from the others
    assert merged.date_payment_emitter == left.date_payment_emitter
    # A merged transfer isn't a source of its own
    assert not merged.hub_values
    assert {t.hub_values for t in merged.merged_transfers.all()} == {
        True,
        False,
    }


@pytest.mark.django_db
def test_merge_transfers_hub_confirmation(db):
    """
    A confirmation in the Hub (no `hub_values`) leaves the values to the
    best value rule.
    """
    dls_left, dls_hub = [
        DataLoadSourceFactory.create(data_source_id=value)
        for value in ["rennes", HUB_DATA_SOURCE]
    ]
    left = TransferFactory.create(
        data_load_sources=[dls_left],
        date_invoice={"value": "2024-03-15", "precision": "day"},
    )
    confirmation = TransferFactory.create(
        data_load_sources=[dls_hub],
        date_invoice={"value": "2024-01-01", "precision": "year"},
    )
    merged = merge_transfers(left, confirmation)
    # The most precise date
    assert merged.date_invoice == left.date_invoice


@pytest.mark.django_db
def test_merge_transfers_resets_computed_fields(db):
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
def test_deduplicate_transferss(db):
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
def test_deduplicate_transfers_multiple_match(db):
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


def day(value: str) -> dict:
    return {"value": value, "precision": "day"}


def year(value: str) -> dict:
    return {"value": f"{value}-01-01", "precision": "year"}


def consortium_supports(agents_left, agents_right, right_dates):
    """
    A 2025 support invoiced by the emitter, and the same support with the
    given dates, e.g. reported by the beneficiary.
    """
    emitter, recipient = EntityFactory.create(), EntityFactory.create()
    values = dict(emitter=emitter, recipient=recipient, amount=1500)
    left = TransferFactory.create(
        **values,
        agents=agents_left,
        currency=None,
        currency_id="EUR",
        date_invoice=day("2025-07-18"),
        date_payment_emitter=None,
        date_payment_recipient=None,
        date_start=day("2025-01-01"),
        date_end=day("2025-12-31"),
    )
    right_values = dict(
        date_invoice=None,
        date_payment_emitter=None,
        date_payment_recipient=None,
    )
    right = TransferFactory.create(
        **values,
        agents=agents_right,
        currency=left.currency,
        currency_id="EUR",
        **{**right_values, **right_dates},
    )
    return left, right


@pytest.mark.django_db
def test_matching_late_receipt_through_intermediary(db):
    """
    Through a shared intermediary, a support received after its contract
    matches the emitter's support of the contract.
    """
    agent = EntityFactory.create()
    left, right = consortium_supports(
        [agent],
        [agent],
        dict(
            date_payment_recipient=day("2026-06-02"),
            date_start=year("2025"),
            date_end=year("2025"),
        ),
    )
    assert transfer_is_matching(left, right) == (True, None)
    assert transfer_is_matching(right, left) == (True, None)


@pytest.mark.django_db
def test_matching_late_receipt_without_shared_intermediary(db):
    left, right = consortium_supports(
        [EntityFactory.create()],
        [EntityFactory.create()],
        dict(
            date_payment_recipient=day("2026-06-02"),
            date_start=year("2025"),
            date_end=year("2025"),
        ),
    )
    assert transfer_is_matching(left, right) == (False, CRITERIA_DATE_CLC)


@pytest.mark.django_db
def test_matching_late_receipt_other_contract(db):
    """The late receipt of the 2026 contract doesn't match the 2025 one."""
    agent = EntityFactory.create()
    left, right = consortium_supports(
        [agent],
        [agent],
        dict(
            date_payment_recipient=day("2026-06-02"),
            date_start=year("2026"),
            date_end=year("2026"),
        ),
    )
    assert transfer_is_matching(left, right)[0] is False


@pytest.mark.django_db
def test_matching_receipt_only_through_intermediary(db):
    """
    A receipt alone is still compared to the other dates: without it, the
    transfer would match the supports of any year.
    """
    agent = EntityFactory.create()
    left, right = consortium_supports(
        [agent], [agent], dict(date_payment_recipient=day("2026-06-02"))
    )
    assert transfer_is_matching(left, right) == (False, CRITERIA_DATE_CLC)
