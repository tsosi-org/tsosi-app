from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from tsosi.app_settings import app_settings
from tsosi.data.exceptions import DataException
from tsosi.models import (
    Currency,
    DataLoadSource,
    Transfer,
    TransferEntityMatching,
)
from tsosi.models.date import (
    DATE_PRECISION_DAY,
    DATE_PRECISION_MONTH,
    DATE_PRECISION_YEAR,
    Date,
)

CRITERIA_EMITTER = "emitter"
CRITERIA_RECIPIENT = "recipient"
CRITERIA_AMOUNT = "amount"
CRITERIA_DATE_INVOICE = "date_invoice"
CRITERIA_DATE_PAYMENT_EMITTER = "date_payment_emitter"
CRITERIA_DATE_PAYMENT_RECIPIENT = "date_payment_recipient"


def date_is_matching(date_left: Date, date_right: Date) -> bool:
    """
    Check if two dates are matching.
    Use the largest precision of the two dates for comparison.
    For example "2025" (year precision) matches "2025-05-10" (day precision).
    """
    date_precision_to_len = {
        DATE_PRECISION_YEAR: 4,
        DATE_PRECISION_MONTH: 7,
        DATE_PRECISION_DAY: 10,
    }
    if date_left is None or date_right is None:
        return True
    largest_precision = max(date_left["precision"], date_right["precision"])
    date_left_precised = date_left["value"][
        : date_precision_to_len[largest_precision]
    ]
    date_right_precised = date_right["value"][
        : date_precision_to_len[largest_precision]
    ]
    return date_left_precised == date_right_precised


def transfer_is_matching(
    transfer_left: Transfer, transfer_right: Transfer
) -> tuple[bool, str | None]:
    """
    Check if two transfers are matching.
    Return a tuple of (is_matching, criteria_not_matching).
    """
    # Check emitter, recipient
    if transfer_left.emitter_id != transfer_right.emitter_id:
        return False, CRITERIA_EMITTER
    if transfer_left.recipient_id != transfer_right.recipient_id:
        return False, CRITERIA_RECIPIENT

    # Check amount
    if not transfer_left.currency or not transfer_right.currency:
        return False, CRITERIA_AMOUNT
    if transfer_left.currency.id == transfer_right.currency.id:
        if not np.isclose(transfer_left.amount, transfer_right.amount):
            return False, CRITERIA_AMOUNT
    elif (
        transfer_right.amounts_clc
        and transfer_left.currency.id in transfer_right.amounts_clc
    ):
        if not np.isclose(
            transfer_left.amount,
            transfer_right.amounts_clc[transfer_left.currency.id],
        ):
            return False, CRITERIA_AMOUNT
    else:
        return False, CRITERIA_AMOUNT

    # Check dates
    for date_field, criteria in [
        ("date_invoice", CRITERIA_DATE_INVOICE),
        ("date_payment_emitter", CRITERIA_DATE_PAYMENT_EMITTER),
        ("date_payment_recipient", CRITERIA_DATE_PAYMENT_RECIPIENT),
    ]:
        if not date_is_matching(
            getattr(transfer_left, date_field),
            getattr(transfer_right, date_field),
        ):
            return False, criteria

    return True, None


def get_non_null(*args: list[float | None]) -> float | None:
    """
    Return the first non-null value from args.
    """
    non_null_values = [value for value in args if value is not None]
    return non_null_values[0] if non_null_values else None


def get_best_amount_and_currency(
    transfer_left: Transfer, transfer_right: Transfer
) -> tuple[float, Currency]:
    """
    Return the best amount and currency from two transfers.
    For now, we just return the left transfer's amount and currency.
    """
    return transfer_left.amount, transfer_left.currency


def get_best_date(
    date_left: Date | None, date_right: Date | None
) -> Date | None:
    """
    Return the best (most precise) date from two dates.
    """
    if date_left is None:
        return date_right
    if date_right is None:
        return date_left
    return (
        date_left
        if date_left["precision"] >= date_right["precision"]
        else date_right
    )


def merge_transfers(
    transfer_left: Transfer, transfer_right: Transfer
) -> Transfer:
    """
    Merge two transfers into one.
    Creates a new Transfer object with the best values from both transfers,
    and update parent transfers, and transfer_entity_matchings.
    """
    fields = {
        "emitter": get_non_null(transfer_left.emitter, transfer_right.emitter),
        "recipient": get_non_null(
            transfer_left.recipient, transfer_right.recipient
        ),
        "agent": get_non_null(transfer_left.agent, transfer_right.agent),
        "date_invoice": get_best_date(
            transfer_left.date_invoice, transfer_right.date_invoice
        ),
        "date_payment_emitter": get_best_date(
            transfer_left.date_payment_emitter,
            transfer_right.date_payment_emitter,
        ),
        "date_payment_recipient": get_best_date(
            transfer_left.date_payment_recipient,
            transfer_right.date_payment_recipient,
        ),
        "date_start": get_best_date(
            transfer_left.date_start, transfer_right.date_start
        ),
        "date_end": get_best_date(
            transfer_left.date_end, transfer_right.date_end
        ),
        "description": get_non_null(
            transfer_left.description, transfer_right.description
        ),
        "hide_amount": transfer_left.hide_amount and transfer_right.hide_amount,
        "original_amount_field": get_non_null(
            transfer_left.original_amount_field,
            transfer_right.original_amount_field,
        ),
        "original_id": get_non_null(
            transfer_left.original_id,
            transfer_right.original_id,
        ),
        "raw_data": {
            transfer_left.data_load_sources.first().data_source_id: transfer_left.raw_data,
            transfer_right.data_load_sources.first().data_source_id: transfer_right.raw_data,
        },
    }
    fields["amount"], fields["currency"] = get_best_amount_and_currency(
        transfer_left, transfer_right
    )
    child = Transfer(**fields)
    child.data_load_sources.set(
        transfer_left.data_load_sources.all()
        | transfer_right.data_load_sources.all(),
    )
    transfer_left.merged_into = child
    transfer_right.merged_into = child
    child.save()
    transfer_left.save()
    transfer_right.save()
    # Update related objects
    for transfer_entity_matching in TransferEntityMatching.objects.filter(
        transfer__in=[transfer_left, transfer_right]
    ):
        transfer_entity_matching.id = None
        transfer_entity_matching.transfer = child
        transfer_entity_matching.save()
    return child


def save_duplicate_matches(
    matches: dict[str, list[str]],
    reverse_matches: dict[str, list[str]],
) -> None:
    """ """
    fields = [
        "data_load_sources__data_source__id",
        "id",
        "original_id",
        "emitter__raw_name",
        "recipient__raw_name",
        "amount",
        "currency__id",
        "date_invoice",
        "date_payment_emitter",
        "date_payment_recipient",
    ]
    output_path = Path(app_settings.ERROR_OUTPUT_FOLDER) / "duplicate_matches"
    output_path.mkdir(exist_ok=True, parents=True)
    for transfer_left_id, transfers_right_ids in matches.items():
        transfer_left = Transfer.objects.filter(id=transfer_left_id)
        transfers_right = Transfer.objects.filter(id__in=transfers_right_ids)
        with pd.ExcelWriter(
            output_path / (str(transfer_left.first().id) + ".xlsx"),
            engine="xlsxwriter",
        ) as writer:
            pd.DataFrame(list(transfer_left.values(*fields))).to_excel(
                writer, sheet_name="transfers_left", index=False
            )
            pd.DataFrame(list(transfers_right.values(*fields))).to_excel(
                writer, sheet_name="transfers_right", index=False
            )


def raise_if_multiple_matches(
    matches: list[tuple[Transfer, Transfer]],
    reverse_matches: list[tuple[Transfer, Transfer]],
    save_matches: bool = False,
) -> None:
    """
    Checks if there are multiple matches in the list of matches.
    I.e if a new transfer matches multiple existing transfers, or if an existing
    transfer matches multiple new transfers.
    Raises a DataException if multiple matches are found.
    """
    multiple_matches = {
        transfer_id: matched_ids
        for transfer_id, matched_ids in matches.items()
        if len(matched_ids) > 1
    }
    multiple_reverse_matches = {
        transfer_id: matched_ids
        for transfer_id, matched_ids in reverse_matches.items()
        if len(matched_ids) > 1
    }
    if save_matches:
        save_duplicate_matches(matches, reverse_matches)
    if multiple_matches:
        raise DataException(
            f"More than one transfer in db matched with a transfer from new source: {multiple_matches}"
        )
    if multiple_reverse_matches:
        raise DataException(
            f"More than one new source transfer matched with a transfer from db: {multiple_reverse_matches}"
        )


def deduplicate_transfers(source: DataLoadSource) -> None:
    """
    Deduplicate transfers from a given data load source against all existing transfers.
    """
    all_other_transfers = Transfer.objects.filter(
        merged_into__isnull=True
    ).exclude(
        data_load_sources__data_source__id__contains=source.data_source.id
    )
    source_transfers = Transfer.objects.filter(
        data_load_sources__data_source__id__contains=source.data_source.id,
        merged_into__isnull=True,
    )
    # Find matches
    matches = defaultdict(list)
    reverse_matches = defaultdict(list)
    for transfer in source_transfers:
        for other_transfer in all_other_transfers:
            is_matching, _ = transfer_is_matching(transfer, other_transfer)
            if is_matching:
                matches[transfer.id].append(other_transfer.id)
                reverse_matches[other_transfer.id].append(transfer.id)
    # Raise if multiple matches found
    raise_if_multiple_matches(matches, reverse_matches, save_matches=True)
    # Merge transfers
    nb_merged = 0
    for transfer_id, matched_ids in matches.items():
        if matched_ids:
            transfer = source_transfers.get(id=transfer_id)
            matched_transfer = all_other_transfers.get(id=matched_ids[0])
            merge_transfers(transfer, matched_transfer)
            nb_merged += 1
    return nb_merged
