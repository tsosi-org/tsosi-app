import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from django.db import transaction
from openpyxl import Workbook
from openpyxl.styles import Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

from tsosi.app_settings import app_settings
from tsosi.data.exceptions import DataException
from tsosi.models import Currency, DataLoadSource, Transfer
from tsosi.models.date import (
    DATE_PRECISION_DAY,
    DATE_PRECISION_MONTH,
    DATE_PRECISION_YEAR,
    Date,
)

CRITERIA_EMITTER = "emitter"
CRITERIA_RECIPIENT = "recipient"
CRITERIA_AMOUNT = "amount"
CRITERIA_SUB_EMITTER = "emitter_sub"
CRITERIA_DATE_INVOICE = "date_invoice"
CRITERIA_DATE_PAYMENT_EMITTER = "date_payment_emitter"
CRITERIA_DATE_PAYMENT_RECIPIENT = "date_payment_recipient"
CRITERIA_DATE_START = "date_start"
CRITERIA_DATE_END = "date_end"
CRITERIA_DATE_CLC = "date_clc"


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
    return date["value"][:10]


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


def get_date_clc(transfer: Transfer) -> Date | None:
    for field in [
        "date_payment_recipient",
        "date_payment_emitter",
        "date_invoice",
    ]:
        if getattr(transfer, field) is not None:
            return getattr(transfer, field)
    if transfer.date_start is not None:
        return {
            **transfer.date_start,
            "precision": DATE_PRECISION_YEAR,
        }
    return None


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
        ("date_start", CRITERIA_DATE_START),
    ]:
        if not date_is_matching(
            getattr(transfer_left, date_field),
            getattr(transfer_right, date_field),
        ):
            return False, criteria

    # Check date clc
    if not date_is_matching(
        get_date_clc(transfer_left),
        get_date_clc(transfer_right),
    ):
        return False, CRITERIA_DATE_CLC

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

    # # Check sub-emitter
    # if transfer_left.emitter_sub != transfer_right.emitter_sub:
    #     return False, CRITERIA_SUB_EMITTER

    # Check amount
    if not transfer_left.currency or not transfer_right.currency:
        return True, None
    elif transfer_left.currency.id == transfer_right.currency.id:
        if not np.isclose(transfer_left.amount, transfer_right.amount, atol=1):
            return False, CRITERIA_AMOUNT
    elif (
        transfer_right.amounts_clc
        and transfer_left.currency.id in transfer_right.amounts_clc
    ):
        if not np.isclose(
            transfer_left.amount,
            transfer_right.amounts_clc[transfer_left.currency.id],
            atol=1,
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
    if not non_null_values:
        return None
    return non_null_values[0]


def get_best_amount_and_currency(
    *transfers: list[Transfer],
) -> tuple[float, Currency]:
    """
    Return the best amount and currency from transfers.
    For now, we just return the first transfer's amount and currency.
    """
    if not transfers:
        return None, None
    return transfers[0].amount, transfers[0].currency


def get_best_date(*dates: list[Date | None]) -> Date | None:
    """
    Return the best (most precise) date from dates.
    """
    non_null_dates = [date for date in dates if date is not None]
    if not non_null_dates:
        return None
    # Sort by precision (day > month > year)
    sorted_dates = sorted(
        non_null_dates,
        key=lambda d: {
            DATE_PRECISION_YEAR: 1,
            DATE_PRECISION_MONTH: 2,
            DATE_PRECISION_DAY: 3,
        }[d["precision"]],
        reverse=True,
    )
    return sorted_dates[0]


MERGE_DATE_FIELDS = [
    "date_invoice",
    "date_payment_emitter",
    "date_payment_recipient",
    "date_start",
    "date_end",
]
# Transfer fields that are never reset when merging into an existing transfer.
MERGE_KEPT_FIELDS = ["id", "date_created", "date_last_updated", "merged_into"]


def get_source_transfers(transfer: Transfer) -> list[Transfer]:
    """
    Return the source transfers of a transfer: the transfers merged into it,
    or the transfer itself if it's not a merged transfer.
    """
    sources = list(transfer.merged_transfers.all())
    return sources or [transfer]


def copy_transfer(transfer: Transfer) -> Transfer:
    """
    Save a copy of the transfer, with a new ID.
    """
    copy = Transfer.objects.get(pk=transfer.pk)
    copy.pk = None
    copy._state.adding = True
    copy.save()
    copy.agents.set(transfer.agents.all())
    copy.data_load_sources.set(transfer.data_load_sources.all())
    return copy


def get_merged_fields(transfers: list[Transfer]) -> dict:
    """
    Compute the fields of the transfer merging the given source transfers.
    """
    fields = {
        "emitter": get_non_null(*[t.emitter for t in transfers]),
        "recipient": get_non_null(*[t.recipient for t in transfers]),
        **{
            field: get_best_date(*[getattr(t, field) for t in transfers])
            for field in MERGE_DATE_FIELDS
        },
        "description": get_non_null(*[t.description for t in transfers]),
        "hide_amount": bool(np.all([t.hide_amount for t in transfers])),
        "original_id": get_non_null(*[t.original_id for t in transfers]),
        "emitter_sub": get_non_null(*[t.emitter_sub for t in transfers]),
    }
    fields["amount"], fields["currency"] = get_best_amount_and_currency(
        *transfers
    )
    return fields


@transaction.atomic
def merge_transfers(
    transfer_left: Transfer, transfer_right: Transfer
) -> Transfer:
    """
    Merge two transfers into one, with the best values of their source
    transfers. Each transfer is either a source transfer or a merged transfer.

    The merged transfer keeps the ID of `transfer_right`, so that the public
    ID of an existing transfer is stable. When `transfer_right` is a source
    transfer, its own data is moved to a copy that becomes one of the sources.
    When `transfer_left` is a merged transfer, its sources are moved to the
    result and it is deleted.
    """
    left_sources = get_source_transfers(transfer_left)
    right_sources = get_source_transfers(transfer_right)
    left_is_merged = left_sources != [transfer_left]
    if right_sources == [transfer_right]:
        right_sources = [copy_transfer(transfer_right)]
    transfers = [*left_sources, *right_sources]

    fields = get_merged_fields(transfers)
    merged = transfer_right
    # Reset the other fields, computed later by the enrichment tasks,
    # as for a new transfer.
    for field in Transfer._meta.concrete_fields:
        if field.name in fields or field.name in MERGE_KEPT_FIELDS:
            continue
        setattr(merged, field.attname, field.get_default())
    for name, value in fields.items():
        setattr(merged, name, value)
    merged.save()
    merged.agents.set(set().union(*[set(t.agents.all()) for t in transfers]))
    merged.data_load_sources.set(
        set().union(*[set(t.data_load_sources.all()) for t in transfers])
    )
    for transfer in transfers:
        transfer.merged_into = merged
        transfer.save()
    if left_is_merged:
        transfer_left.delete()
    return merged


def save_matches(
    matches: list[tuple[str, str]],
    to_check: list[tuple[str, str]],
) -> Path:
    fields = [
        "id",
        "original_id",
        "emitter__name",
        "recipient__name",
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
                Transfer.objects.filter(
                    merged_into__isnull=True,
                    id__in=[transfer_left, transfer_right],
                ).values(*fields)
            )
        )
    for transfer_left, transfer_right in to_check:
        full_to_check.extend(
            list(
                Transfer.objects.filter(
                    merged_into__isnull=True,
                    id__in=[transfer_left, transfer_right],
                ).values(*fields)
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
    ws.column_dimensions["M"].width = 12
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
    ).exclude(data_load_sources__data_source_id=source.data_source_id)
    source_transfers = Transfer.objects.filter(
        merged_into__isnull=True,
        data_load_sources=source,
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
