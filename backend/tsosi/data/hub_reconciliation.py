"""
Reconciliation in the Data Contribution Hub: the saved supports that may be
the one an organization is entering (matches), and the possible duplicates
among its saved supports. Both use the criteria of the ingestion's
deduplication (`match_candidate`), the amount excepted: a support declared
with another amount may still be the same.

The saved supports are the rows of the organization's supports table: its
published supports (keyed by transfer ID), with the values of their pending
edit if any, and its pending new supports (`new-<declaration ID>`). Only the
supports emitted by the organization itself are compared, not those of its
children: each organization manages its own supports.
"""

from django.db.models import Q, QuerySet

from tsosi.data.ingestion.transfer_matching import (
    MATCH_AMOUNT_DIFFERS,
    match_candidate,
)
from tsosi.models import Declaration, Entity, Transfer
from tsosi.models.declaration import (
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_STATUS_APPROVED,
    DECLARATION_STATUSES_PENDING,
)

DATE_FIELDS = [
    "date_invoice",
    "date_payment_emitter",
    "date_payment_recipient",
    "date_start",
    "date_end",
]


def new_row_key(declaration_id: int) -> str:
    """The row of a pending new support in the supports table."""
    return f"new-{declaration_id}"


def own_supports(entity: Entity) -> QuerySet:
    """The published transfers emitted by the organization."""
    return (
        Transfer.objects.filter(merged_into__isnull=True, emitter=entity)
        .select_related("currency")
        .order_by("-date_clc", "id")
    )


def declared_transfer(
    entity: Entity,
    recipient: Entity,
    amount: float | None = None,
    currency=None,
    **dates,
) -> Transfer:
    """
    An unsaved transfer of the organization with the declared values, to
    match against the saved ones.
    """
    if amount is None:
        currency = None
    return Transfer(
        emitter=entity,
        recipient=recipient.sucessor_or_self(),
        amount=amount,
        currency=currency,
        **{f: dates.get(f) for f in DATE_FIELDS},
    )


def declaration_transfer(declaration: Declaration) -> Transfer:
    """An unsaved transfer with the declared values."""
    return declared_transfer(
        declaration.entity,
        declaration.recipient,
        amount=declaration.amount,
        currency=declaration.currency,
        **{f: getattr(declaration, f) for f in DATE_FIELDS},
    )


def saved_supports(
    entity: Entity, transfers: list[Transfer]
) -> dict[str, Transfer]:
    """
    The organization's saved supports, by row: the given published ones,
    with the values of their pending edit, and its pending new supports.
    """
    pending = (
        Declaration.objects.pending()
        .filter(
            entity=entity,
            kind__in=[DECLARATION_KIND_NEW, DECLARATION_KIND_EDIT],
            recipient__isnull=False,
        )
        .select_related("entity", "recipient", "currency")
        .order_by("date_created")
    )
    edits = {
        d.transfer_id: d for d in pending if d.kind == DECLARATION_KIND_EDIT
    }
    rows = {}
    for transfer in transfers:
        edit = edits.get(transfer.id)
        rows[str(transfer.id)] = (
            declaration_transfer(edit) if edit else transfer
        )
    for declaration in pending:
        if declaration.kind == DECLARATION_KIND_NEW:
            rows[new_row_key(declaration.id)] = declaration_transfer(
                declaration
            )
    return rows


def matching_rows(
    transfer: Transfer, rows: dict[str, Transfer]
) -> list[tuple[str, bool]]:
    """
    The rows that may be the transfer, with whether their amount differs:
    those with the same amount first. None without any date, as every
    support to the beneficiary would match.
    """
    if not any(getattr(transfer, f) for f in DATE_FIELDS):
        return []
    matches = []
    for key, candidate in rows.items():
        if candidate.recipient_id != transfer.recipient_id:
            continue
        match = match_candidate(transfer, candidate)
        if match is not None:
            matches.append((key, match == MATCH_AMOUNT_DIFFERS))
    return sorted(matches, key=lambda m: m[1])


def find_matches(
    entity: Entity, transfer: Transfer, exclude: str | None = None
) -> list[tuple[str, bool]]:
    """
    The organization's saved supports that may be the transfer being
    entered (see `matching_rows`), the row being edited excepted.
    """
    rows = saved_supports(entity, list(own_supports(entity)))
    rows.pop(exclude, None)
    return matching_rows(transfer, rows)


def find_published_matches(entity: Entity, transfer: Transfer) -> list[str]:
    """The IDs of the published supports that may be the transfer."""
    rows = {str(t.id): t for t in own_supports(entity)}
    return [key for key, _ in matching_rows(transfer, rows)]


def reconciled_pairs(
    entity: Entity, transfers: list[Transfer]
) -> set[frozenset]:
    """
    The pairs of rows that the organization declared to be different
    supports, or the same one (pending merges): not-duplicates, and new
    supports with the matches they aren't, approved or pending. The
    transfers of the approved ones may have been merged since: they're found
    through the sources of the given public transfers.
    """
    public_ids = {}
    for transfer in transfers:
        public_ids[transfer.id] = str(transfer.id)
        for source in transfer.merged_transfers.all():
            public_ids[source.id] = str(transfer.id)

    def new_key(declaration: Declaration) -> str | None:
        if declaration.status == DECLARATION_STATUS_APPROVED:
            return public_ids.get(declaration.published_transfer_id)
        return new_row_key(declaration.id)

    statuses = [DECLARATION_STATUS_APPROVED, *DECLARATION_STATUSES_PENDING]
    declarations = (
        Declaration.objects.filter(entity=entity)
        .filter(
            Q(
                kind__in=[DECLARATION_KIND_NEW, DECLARATION_KIND_NOT_DUPLICATE],
                status__in=statuses,
            )
            | Q(
                kind=DECLARATION_KIND_MERGE,
                status__in=DECLARATION_STATUSES_PENDING,
            )
        )
        .prefetch_related("other_transfers", "other_declarations")
    )
    pairs = set()
    for declaration in declarations:
        if declaration.kind == DECLARATION_KIND_NEW:
            main = new_key(declaration)
        else:
            main = public_ids.get(declaration.transfer_id)
        others = [
            public_ids.get(t.id) for t in declaration.other_transfers.all()
        ]
        others += [new_key(d) for d in declaration.other_declarations.all()]
        for other in others:
            if main and other and main != other:
                pairs.add(frozenset((main, other)))
    return pairs


def possible_duplicates(entity: Entity) -> list[tuple[str, str]]:
    """
    The pairs of the organization's saved supports that may be the same
    support (see `saved_supports`), those it reconciled excepted.
    """
    transfers = list(own_supports(entity).prefetch_related("merged_transfers"))
    rows = list(saved_supports(entity, transfers).items())
    reconciled = reconciled_pairs(entity, transfers)
    pairs = []
    for index, (left_key, left) in enumerate(rows):
        for right_key, right in rows[index + 1 :]:
            if left.recipient_id != right.recipient_id:
                continue
            if frozenset((left_key, right_key)) in reconciled:
                continue
            if match_candidate(left, right) is not None:
                pairs.append((left_key, right_key))
    return pairs
