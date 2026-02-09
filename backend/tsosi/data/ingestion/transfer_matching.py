import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from tsosi.app_settings import app_settings
from tsosi.data.exceptions import DataException
from tsosi.models import (
    Currency,
    DataLoadSource,
    Transfer,
    TransferEntityMatching,
)
from tsosi.models.date import (
    DATE_PRECISION_MONTH,
    DATE_PRECISION_YEAR,
    Date,
    format_date,
)
from tsosi.models.transfer import MATCH_CRITERIA_MERGED
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC

CRITERIA_EMITTER = "emitter"
CRITERIA_RECIPIENT = "recipient"
CRITERIA_AMOUNT = "amount"
CRITERIA_DATE_INVOICE = "date_invoice"
CRITERIA_DATE_PAYMENT_EMITTER = "date_payment_emitter"
CRITERIA_DATE_PAYMENT_RECIPIENT = "date_payment_recipient"
CRITERIA_DATE_START = "date_start"
CRITERIA_DATE_END = "date_end"


def format_date(date: Date | None, precision: str | None = None) -> str | None:
    """
    Format a Date object to string based on its precision.
    """
    if date is None:
        return None
    if precision is None:
        precision = date["precision"]
    if precision == DATE_PRECISION_YEAR:
        return date["value"][:4]
    elif precision == DATE_PRECISION_MONTH:
        return date["value"][:7]
    return date["value"]


def date_contains(
    date_start: Date | None, date_end: Date | None, date_check: Date | None
) -> bool:
    """
    Check if date_check is within the range of date_start and date_end.
    If any is None, consider it True.
    """
    if date_check is None:
        return True
    if date_start is not None:
        largest_precision = max(
            date_start["precision"], date_check["precision"]
        )
        if format_date(date_check, largest_precision) < format_date(
            date_start, largest_precision
        ):
            return False
    if date_end is not None:
        largest_precision = max(date_end["precision"], date_check["precision"])
        if format_date(date_check, largest_precision) > format_date(
            date_end, largest_precision
        ):
            return False
    return True


def date_is_matching(date_left: Date, date_right: Date) -> bool:
    """
    Check if two dates are matching.
    Use the largest precision of the two dates for comparison.
    For example "2025" (year precision) matches "2025-05-10" (day precision).
    """
    if date_left is None or date_right is None:
        return True
    largest_precision = max(date_left["precision"], date_right["precision"])
    date_left_precised = format_date(date_left, largest_precision)
    date_right_precised = format_date(date_right, largest_precision)
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

    # Check dates
    for date_field, criteria in [
        ("date_invoice", CRITERIA_DATE_INVOICE),
        ("date_payment_emitter", CRITERIA_DATE_PAYMENT_EMITTER),
        ("date_payment_recipient", CRITERIA_DATE_PAYMENT_RECIPIENT),
        ("date_start", CRITERIA_DATE_END),
        ("date_end", CRITERIA_DATE_START),
    ]:
        if not date_is_matching(
            getattr(transfer_left, date_field),
            getattr(transfer_right, date_field),
        ):
            return False, criteria

    # Check date ranges
    for a, b in [
        (transfer_left, transfer_right),
        (transfer_right, transfer_left),
    ]:
        for date_field, criteria in [
            ("date_invoice", CRITERIA_DATE_INVOICE),
            ("date_payment_emitter", CRITERIA_DATE_PAYMENT_EMITTER),
            ("date_payment_recipient", CRITERIA_DATE_PAYMENT_RECIPIENT),
        ]:
            if not (
                date_contains(
                    a.date_start,
                    a.date_end,
                    getattr(b, date_field),
                )
            ):
                return False, criteria
            elif getattr(b, date_field) is not None:
                break

    # Check amount
    if not transfer_left.currency or not transfer_right.currency:
        return False, CRITERIA_AMOUNT
    elif transfer_left.currency.id == transfer_right.currency.id:
        if not np.isclose(transfer_left.amount, transfer_right.amount):
            return False, CRITERIA_AMOUNT
    elif (
        transfer_right.amounts_clc
        and transfer_left.currency.id in transfer_right.amounts_clc
    ):
        if not np.isclose(
            transfer_left.amount,
            transfer_right.amounts_clc[transfer_left.currency.id],
            atol=0.1,
        ):
            return False, CRITERIA_AMOUNT
    else:
        return False, CRITERIA_AMOUNT

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
    # Merge amount and currency
    fields["amount"], fields["currency"] = get_best_amount_and_currency(
        transfer_left, transfer_right
    )
    # Merge raw_data
    raw_data = {
        transfer_left.data_load_sources.first().data_source_id: transfer_left.raw_data
    }
    if transfer_right.data_load_sources.count() > 1:
        for dls in transfer_right.data_load_sources.all():
            raw_data[dls.data_source_id] = transfer_right.raw_data[
                dls.data_source_id
            ]
    else:
        raw_data[transfer_right.data_load_sources.first().data_source_id] = (
            transfer_right.raw_data
        )
    fields["raw_data"] = raw_data
    # Merge sub_entity
    sub_entity = get_non_null(
        transfer_left.transferentitymatching_set.filter(
            transfer_entity_type="emitter"
        )
        .first()
        .sub_entity,
        transfer_right.transferentitymatching_set.filter(
            transfer_entity_type="emitter"
        )
        .first()
        .sub_entity,
    )
    # Merge transfers
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
    # Create new TransferEntityMatching for child
    for entity_type in ["emitter", "recipient", "agent"]:
        entity = getattr(child, entity_type)
        if entity is None:
            continue
        tem = TransferEntityMatching.objects.create(
            transfer_entity_type=entity_type,
            match_criteria=MATCH_CRITERIA_MERGED,
            match_source=MATCH_SOURCE_AUTOMATIC,
            entity=entity,
            transfer=child,
        )
        if entity_type == "emitter" and sub_entity is not None:
            tem.sub_entity = sub_entity
            tem.save()
    return child


def save_matches(
    matches: list[tuple[str, str]],
    to_check: list[tuple[str, str]],
) -> Path:
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
        "date_start",
        "date_end",
    ]
    output_path = Path(app_settings.ERROR_OUTPUT_FOLDER) / "duplicate_matches"
    shutil.rmtree(output_path) if output_path.exists() else None
    output_path.mkdir(exist_ok=True, parents=True)
    full_matches = []
    full_to_check = []
    for transfer_left, transfer_right in matches:
        full_matches.extend(
            list(
                Transfer.objects.filter(id__in=[transfer_left, transfer_right])
                .order_by("data_load_sources__data_source__id")
                .values(*fields)
            )
        )
    for transfer_left, transfer_right in to_check:
        full_to_check.extend(
            list(
                Transfer.objects.filter(id__in=[transfer_left, transfer_right])
                .order_by("data_load_sources__data_source__id")
                .values(*fields)
            )
        )

    wb = Workbook()
    ws = wb.active
    border = Border(bottom=Side(border_style="double", color="000000"))
    df_match = pd.DataFrame(full_matches, columns=fields)
    df_match["match"] = True
    df_to_check = pd.DataFrame(full_to_check, columns=fields)
    df_to_check["match"] = False
    df = pd.concat([df_match, df_to_check], ignore_index=True)
    df["date_invoice"] = df["date_invoice"].apply(format_date)
    df["date_payment_emitter"] = df["date_payment_emitter"].apply(format_date)
    df["date_payment_recipient"] = df["date_payment_recipient"].apply(
        format_date
    )
    df["date_start"] = df["date_start"].apply(format_date)
    df["date_end"] = df["date_end"].apply(format_date)
    for r_idx, row in enumerate(
        dataframe_to_rows(df.astype(str), index=False),
        1,
    ):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            if value != "None":
                cell.value = value
            if r_idx % 2 == 1:
                cell.border = border
    ws.auto_filter.ref = ws.dimensions
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 22
    ws.column_dimensions["H"].width = 12
    ws.column_dimensions["I"].width = 12
    ws.column_dimensions["J"].width = 12
    ws.column_dimensions["K"].width = 12
    ws.column_dimensions["L"].width = 12
    wb.save(output_path / "all_matches.xlsx")
    return output_path


def raise_if_multiple_matches(
    matches: list[tuple[str, str]],
    to_check: list[tuple[str, str]],
) -> None:
    """
    Checks if there are multiple matches in the list of matches.
    I.e if a new transfer matches multiple existing transfers, or if an existing
    transfer matches multiple new transfers.
    Raises a DataException if multiple matches are found.
    """
    if not matches:
        return
    left_ids, right_ids = zip(*matches)
    pathname = save_matches(matches, to_check)
    if len(set(left_ids)) < len(left_ids) or len(set(right_ids)) < len(
        right_ids
    ):
        raise DataException(
            f"Failed to deduplicate transfers: see {pathname} for details"
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
    matches = []
    to_check = []
    for transfer in source_transfers:
        for other_transfer in all_other_transfers:
            is_matching, reason = transfer_is_matching(transfer, other_transfer)
            if is_matching:
                matches.append((transfer.id, other_transfer.id))
            elif reason == CRITERIA_AMOUNT:
                to_check.append((transfer.id, other_transfer.id))
    # Raise if multiple matches found
    raise_if_multiple_matches(matches, to_check)
    # Merge transfers
    nb_merged = 0
    for transfer_id, matched_id in matches:
        transfer = source_transfers.get(id=transfer_id)
        matched_transfer = all_other_transfers.get(id=matched_id)
        merge_transfers(transfer, matched_transfer)
        nb_merged += 1
    return nb_merged
