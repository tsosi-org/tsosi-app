"""
Submission and publication of the declarations of the Data Contribution Hub.

Members submit their organization's draft declarations, which become
read-only. When the TSOSI team approves the submission (Django admin), a
Celery task publishes them in one transaction: they become the
organization's own source transfers, from one `DataLoadSource` of the
`tsosi_portal` data source, merged with the other sources' transfers as for
ingested data, the values of its new supports and edits winning (see
`by_precedence`).
This bypasses the file ingestion and its overlap checks, which assume
immutable datasets.

The published values that the declarations refer to are kept at submission
(`Submission.snapshot`): if they changed since, e.g. with a new ingest, the
approval stops and the submission shows the conflicting declarations.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import TypeVar

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from tsosi.app_settings import app_settings
from tsosi.data.hub_reconciliation import (
    DATE_FIELDS,
    declaration_transfer,
    find_published_matches,
)
from tsosi.data.ingestion.transfer_matching import (
    get_date_clc,
    get_source_transfers,
    merge_transfers,
    update_merged_transfer,
)
from tsosi.data.signals import transfers_created
from tsosi.models import (
    DataLoadSource,
    DataSource,
    Declaration,
    Entity,
    Submission,
    Transfer,
)
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_KINDS_SUPPORT_CHANGES,
    DECLARATION_KINDS_WITH_VALUES,
    DECLARATION_STATUS_APPROVED,
    DECLARATION_STATUS_DRAFT,
    DECLARATION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_APPROVED,
    SUBMISSION_STATUS_PUBLISHING,
    SUBMISSION_STATUS_RETURNED,
    SUBMISSION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_TO_CHECK
from tsosi.models.static_data import HUB_DATA_SOURCE

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PublicationConflict(Exception):
    """The published data changed since the submission."""

    def __init__(self, conflicts: list[str]):
        super().__init__("\n".join(conflicts))
        self.conflicts = conflicts


class SubmissionNotPending(Exception):
    """
    The submission isn't waiting for approval any more, e.g. approved or
    returned by another request at the same time.
    """


def lock_submission(submission: Submission, statuses: list[str]) -> Submission:
    """
    The submission, locked until the end of the transaction, if it has one
    of the statuses: two approvals at once (a double click) don't both
    publish it.
    """
    locked = Submission.objects.select_for_update().get(id=submission.id)
    if locked.status not in statuses:
        raise SubmissionNotPending(
            f"Submission {submission.id} is {locked.status}."
        )
    return locked


def load_declarations(declarations) -> list[Declaration]:
    return list(
        declarations.select_related("recipient", "transfer")
        .prefetch_related("agents", "other_transfers", "other_declarations")
        .order_by("date_created", "id")
    )


def transfer_snapshot(transfer: Transfer) -> dict:
    """The published values of a transfer that a declaration relies on."""
    return {
        "id": str(transfer.id),
        "merged_into": (
            str(transfer.merged_into_id) if transfer.merged_into_id else None
        ),
        "emitter": str(transfer.emitter_id),
        "recipient": str(transfer.recipient_id),
        "agents": sorted(str(a.id) for a in transfer.agents.all()),
        "amount": transfer.amount,
        "currency": transfer.currency_id,
        **{f: getattr(transfer, f) for f in DATE_FIELDS},
    }


def submission_snapshot(declarations: list[Declaration]) -> dict:
    """
    The published values of the transfers that the declarations refer to,
    by declaration: `{id: {"transfer": values, "other_transfers": [...]}}`.
    """
    return {
        str(d.id): {
            "transfer": transfer_snapshot(d.transfer) if d.transfer else None,
            "other_transfers": [
                transfer_snapshot(t) for t in d.other_transfers.all()
            ],
        }
        for d in declarations
    }


class DraftsChanged(Exception):
    """
    The drafts aren't those previewed any more, e.g. added, removed or
    edited by another member since.
    """


def draft_values(declaration: Declaration) -> dict:
    """Everything that a draft declaration submits."""
    return {
        "id": declaration.id,
        "kind": declaration.kind,
        "transfer": declaration.transfer_id,
        "other_transfers": sorted(
            str(t.id) for t in declaration.other_transfers.all()
        ),
        "other_declarations": sorted(
            d.id for d in declaration.other_declarations.all()
        ),
        "recipient": declaration.recipient_id,
        "agents": sorted(str(a.id) for a in declaration.agents.all()),
        "amount": declaration.amount,
        "currency": declaration.currency_id,
        **{f: getattr(declaration, f) for f in DATE_FIELDS},
    }


def drafts_hash(declarations: list[Declaration]) -> str:
    """
    A SHA-256 hash of the draft declarations' values: the preview gives it,
    and the submission checks that the drafts didn't change since.
    """
    values = sorted(
        (draft_values(d) for d in declarations), key=lambda v: v["id"]
    )
    serialized = json.dumps(values, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


@transaction.atomic
def submit_declarations(
    entity: Entity,
    user,
    declaration_ids: list[int] | None = None,
    declarations_hash: str | None = None,
) -> Submission | None:
    """
    Submit the organization's draft declarations for approval, as one
    submission: they become read-only. None if there's no draft.
    With `declaration_ids` and `declarations_hash`, the drafts that the
    member previewed and their hash (`drafts_hash`), raise `DraftsChanged`
    if the drafts are others, or were edited since: the consent is for what
    was previewed.
    """
    # Only the declarations: their nullable relations are outer joins
    drafts = Declaration.objects.select_for_update(of=("self",)).filter(
        entity=entity, status=DECLARATION_STATUS_DRAFT
    )
    declarations = load_declarations(drafts)
    if declaration_ids is not None and {d.id for d in declarations} != set(
        declaration_ids
    ):
        raise DraftsChanged
    if declarations_hash is not None and (
        drafts_hash(declarations) != declarations_hash
    ):
        raise DraftsChanged
    if not declarations:
        return None
    submission = Submission.objects.create(
        entity=entity,
        submitted_by=user,
        consent_at=timezone.now(),
        snapshot=submission_snapshot(declarations),
    )
    for declaration in declarations:
        declaration.status = DECLARATION_STATUS_SUBMITTED
        declaration.submission = submission
        declaration.save()
    logger.info(
        f"Submission {submission.id} of {len(declarations)} declarations "
        f"by {user.email} for {entity.id}."
    )
    return submission


def is_source(entity: Entity, transfer: Transfer) -> bool:
    return transfer.data_load_sources.filter(entity=entity).exists()


def declaration_conflict(
    entity: Entity, declaration: Declaration, snapshot: dict
) -> str | None:
    """
    Why the declaration can't be published any more, if it can't: the
    transfers it refers to changed, or its rules don't hold any more.
    """
    expected = [snapshot["transfer"]] if snapshot.get("transfer") else []
    expected += snapshot.get("other_transfers", [])
    for values in expected:
        current = Transfer.objects.filter(id=values["id"]).first()
        if current is None:
            return "a support it refers to was deleted since the submission."
        if transfer_snapshot(current) != values:
            return "a support it refers to changed since the submission."
    kind = declaration.kind
    if kind != DECLARATION_KIND_NEW and declaration.transfer is None:
        return "the support it refers to was deleted since the submission."
    if kind == DECLARATION_KIND_CONFIRMATION and is_source(
        entity, declaration.transfer
    ):
        return "the organization declared this support since the submission."
    if kind == DECLARATION_KIND_REMOVAL and not is_source(
        entity, declaration.transfer
    ):
        return "the organization isn't a source of this support any more."
    if kind == DECLARATION_KIND_NEW:
        dismissed = {str(t.id) for t in declaration.other_transfers.all()}
        matches = find_published_matches(
            entity, declaration_transfer(declaration)
        )
        if any(key not in dismissed for key in matches):
            return (
                "a support that may be the same was published since the "
                "submission: return it to the member to reconcile it."
            )
    return None


def check_conflicts(
    entity: Entity, declarations: list[Declaration], snapshot: dict | None
) -> list[str]:
    """The declarations that can't be published any more, and why."""
    conflicts = []
    for declaration in declarations:
        problem = declaration_conflict(
            entity, declaration, (snapshot or {}).get(str(declaration.id), {})
        )
        if problem:
            conflicts.append(
                f"{declaration.get_kind_display()} #{declaration.id}: "
                f"{problem}"
            )
    return conflicts


def declared_values(declaration: Declaration) -> dict:
    """
    The values of a new support or an edit, for the organization's source
    transfer: they win when merged.
    """
    return {
        "hub_values": True,
        "recipient": declaration.recipient.sucessor_or_self(),
        "amount": declaration.amount,
        "currency": declaration.currency,
        **{f: getattr(declaration, f) for f in DATE_FIELDS},
    }


def declared_agents(declaration: Declaration) -> set[Entity]:
    return {a.sucessor_or_self() for a in declaration.agents.all()}


def transfer_values(transfer: Transfer) -> dict:
    """The values of a transfer, to copy into the organization's own."""
    return {
        "emitter": transfer.emitter,
        "emitter_sub": transfer.emitter_sub,
        "recipient": transfer.recipient,
        "amount": transfer.amount,
        "currency": transfer.currency,
        "description": transfer.description,
        "hide_amount": transfer.hide_amount,
        **{f: getattr(transfer, f) for f in DATE_FIELDS},
    }


def create_source(
    declaration: Declaration,
    data_load_source: DataLoadSource,
    agents,
    **values,
) -> Transfer:
    """The organization's source transfer of the declaration."""
    values.setdefault("description", "")
    transfer = Transfer.objects.create(
        original_id=f"hub-{declaration.id}", **values
    )
    transfer.agents.set(agents)
    transfer.data_load_sources.add(data_load_source)
    declaration.published_transfer = transfer
    return transfer


def own_sources(entity: Entity, transfer: Transfer) -> list[Transfer]:
    """
    The organization's source transfers of the public transfer: those from
    its data loads.
    """
    return [s for s in get_source_transfers(transfer) if is_source(entity, s)]


def resolve(transfer_id, survivors: dict) -> Transfer | None:
    """
    The public transfer that a transfer is, or was merged into, during the
    publication. `survivors` maps the transfers deleted by a merge to the
    result.
    """
    while transfer_id in survivors:
        transfer_id = survivors[transfer_id]
    transfer = Transfer.objects.filter(id=transfer_id).first()
    while transfer is not None and transfer.merged_into_id is not None:
        transfer = transfer.merged_into
    return transfer


def merge_order(a: Transfer, b: Transfer) -> tuple[Transfer, Transfer]:
    """
    The left and right transfers to merge: `merge_transfers` keeps the right
    one's ID and deletes the left one if it's a merged transfer. A source
    transfer goes left, kept as a source; else the older one is kept.
    """
    a_merged, b_merged = (
        a.merged_transfers.exists(),
        b.merged_transfers.exists(),
    )
    if a_merged != b_merged:
        return (b, a) if a_merged else (a, b)
    return (b, a) if a.date_created <= b.date_created else (a, b)


def publish_merge(declaration: Declaration, survivors: dict) -> Transfer | None:
    merged = resolve(declaration.transfer_id, survivors)
    for other in declaration.other_transfers.all():
        other = resolve(other.id, survivors)
        if merged is None or other is None or merged.id == other.id:
            continue
        left, right = merge_order(merged, other)
        left_is_merged = left.merged_transfers.exists()
        merged = merge_transfers(left, right)
        if left_is_merged:
            survivors[left.id] = merged.id
    return merged


def publish_confirmation(
    entity: Entity,
    declaration: Declaration,
    public: Transfer,
    data_load_source: DataLoadSource,
) -> Transfer:
    """
    The organization's own transfer with the public transfer's values,
    merged with it. The other sources' transfers are untouched, and their
    values still apply (not `hub_values`).
    """
    source = create_source(
        declaration,
        data_load_source,
        public.agents.all(),
        **transfer_values(public),
    )
    return merge_transfers(source, public)


def publish_edit(
    entity: Entity,
    declaration: Declaration,
    public: Transfer,
    data_load_source: DataLoadSource,
) -> Transfer:
    """
    The organization's own transfer with its values, merged with the public
    transfer: its values win. If it already declared the support, its
    previous source transfer is updated, its old values kept in the history.
    """
    values = {**declared_values(declaration), "emitter": public.emitter}
    agents = declared_agents(declaration)
    own = own_sources(entity, public)
    if not own:
        source = create_source(declaration, data_load_source, agents, **values)
        return merge_transfers(source, public)
    source = public if own[0].id == public.id else own[0]
    for name, value in values.items():
        setattr(source, name, value)
    # Computed again by the enrichment tasks
    source.date_clc = None
    source.amounts_clc = None
    source.save()
    source.agents.set(agents)
    source.data_load_sources.remove(
        *source.data_load_sources.filter(entity=entity)
    )
    source.data_load_sources.add(data_load_source)
    declaration.published_transfer = source
    if source.id != public.id:
        update_merged_transfer(public, list(public.merged_transfers.all()))
    return public


def publish_removal(
    entity: Entity,
    declaration: Declaration,
    public: Transfer,
    data_load_source: DataLoadSource,
) -> Transfer | None:
    """
    Delete the organization's source transfers of the public transfer, which
    is computed again from the remaining ones, keeping its ID. It's deleted
    too if no source is left.
    """
    own_ids = {s.id for s in own_sources(entity, public)}
    sources = get_source_transfers(public)
    remaining = [s for s in sources if s.id not in own_ids]
    for source in sources:
        if source.id in own_ids and source.id != public.id:
            source.delete()
    if not remaining:
        public.delete()
        return None
    update_merged_transfer(public, remaining)
    return public


SUPPORT_CHANGE_PUBLISHERS = {
    DECLARATION_KIND_CONFIRMATION: publish_confirmation,
    DECLARATION_KIND_EDIT: publish_edit,
    DECLARATION_KIND_REMOVAL: publish_removal,
}


def set_recipients_scope(declarations: list[Declaration]):
    """
    The declared beneficiaries without scope, added in the Hub or not, are
    to be checked by the TSOSI team.
    """
    for declaration in declarations:
        if declaration.kind not in DECLARATION_KINDS_WITH_VALUES:
            continue
        recipient = declaration.recipient.sucessor_or_self()
        if recipient.scope is None:
            recipient.scope = ENTITY_SCOPE_TO_CHECK
            recipient.save()


def apply_declarations(
    entity: Entity,
    declarations: list[Declaration],
    data_load_source: DataLoadSource,
) -> dict[int, Transfer | None]:
    """
    Publish the declarations: the merges first, then the changes of
    supports, whose transfers may have been merged, then the new supports.
    Not-duplicates publish nothing: their approval is their record.
    Return the resulting public transfer of each declaration, if any.
    """
    set_recipients_scope(declarations)
    survivors = {}
    results = {}
    for declaration in declarations:
        if declaration.kind == DECLARATION_KIND_MERGE:
            results[declaration.id] = publish_merge(declaration, survivors)
    for declaration in declarations:
        if declaration.kind in DECLARATION_KINDS_SUPPORT_CHANGES:
            public = resolve(declaration.transfer_id, survivors)
            publisher = SUPPORT_CHANGE_PUBLISHERS[declaration.kind]
            results[declaration.id] = publisher(
                entity, declaration, public, data_load_source
            )
    for declaration in declarations:
        if declaration.kind == DECLARATION_KIND_NEW:
            results[declaration.id] = create_source(
                declaration,
                data_load_source,
                declared_agents(declaration),
                emitter=entity,
                **declared_values(declaration),
            )
        elif declaration.kind == DECLARATION_KIND_NOT_DUPLICATE:
            results[declaration.id] = None
    return results


def create_data_load_source(
    entity: Entity, date: datetime, name: str
) -> DataLoadSource:
    """The partial data load of the organization's declarations."""
    DataSource.objects.get_or_create(id=HUB_DATA_SOURCE)
    return DataLoadSource.objects.create(
        data_source_id=HUB_DATA_SOURCE,
        data_load_name=name[:128],
        full_data=False,
        date_data_obtained=timezone.localdate(date),
        entity=entity,
    )


def publish_submission(submission: Submission, user) -> None:
    """
    Publish the declarations of an approved submission (`PUBLISHING`), in
    one transaction, and trigger the enrichment of the new transfers. Raise
    `PublicationConflict`, with nothing published, if the published data
    changed since the submission, and `SubmissionNotPending` if it's not
    being published.
    """
    # Imported here: the enrichment imports the ingestion, which imports it
    from tsosi.data.enrichment.database_related import update_entity_hide_amount

    entity = submission.entity
    with transaction.atomic():
        # Approved only: not a submission returned to the team by a failed
        # publication, e.g. on a redelivered task
        submission = lock_submission(submission, [SUBMISSION_STATUS_PUBLISHING])
        declarations = load_declarations(submission.declarations.all())
        conflicts = check_conflicts(entity, declarations, submission.snapshot)
        if conflicts:
            raise PublicationConflict(conflicts)
        data_load_source = create_data_load_source(
            entity,
            submission.consent_at or submission.date_created,
            f"Hub submission {submission.id} · {entity.name}",
        )
        apply_declarations(entity, declarations, data_load_source)
        for declaration in declarations:
            declaration.status = DECLARATION_STATUS_APPROVED
            # Deleted by the publication, e.g. a removed support
            if not Transfer.objects.filter(id=declaration.transfer_id).exists():
                declaration.transfer = None
            declaration.save()
        submission.status = SUBMISSION_STATUS_APPROVED
        submission.approved_by = user
        submission.approved_at = timezone.now()
        submission.data_load_source = data_load_source
        submission.publication_error = None
        submission.save()
        update_entity_hide_amount(entity)
    logger.info(
        f"Published submission {submission.id}: {len(declarations)} "
        f"declarations of {entity.id}."
    )
    transfers_created.send(None)


@contextmanager
def history_user(user):
    """
    Record the changes with the user in the history, outside of a request
    (Celery task), as `HistoryRequestMiddleware` does for requests.
    """
    context = HistoricalRecords.context
    previous = getattr(context, "request", None)
    context.request = SimpleNamespace(user=user)
    try:
        yield
    finally:
        if previous is None:
            del context.request
        else:
            context.request = previous


def run_publication(submission_id: int, user_id: int | None) -> None:
    """
    Publish an approved submission (Celery task). On failure, it waits for
    approval again, with the error.
    """
    submission = Submission.objects.select_related("entity").get(
        id=submission_id
    )
    if submission.status != SUBMISSION_STATUS_PUBLISHING:
        logger.warning(
            f"Submission {submission_id} is {submission.status}: "
            "not published."
        )
        return
    user = get_user_model().objects.filter(id=user_id).first()
    try:
        with history_user(user):
            publish_submission(submission, user)
    except SubmissionNotPending as error:
        # Published by another run of the task in the meantime
        logger.warning(f"{error} Not published.")
    except PublicationConflict as error:
        fail_publication(submission, user, "\n".join(error.conflicts))
    except Exception:
        fail_publication(
            submission,
            user,
            "The publication failed with an unexpected error: see the logs.",
        )
        raise


def fail_publication(submission: Submission, user, error: str):
    logger.warning(f"Submission {submission.id} not published: {error}")
    submission.refresh_from_db()
    submission.status = SUBMISSION_STATUS_SUBMITTED
    submission.publication_error = error
    with history_user(user):
        submission.save()


def approve_submission(submission: Submission, user) -> None:
    """
    Approve a submission: queue its publication as a Celery task, so that it
    doesn't run at the same time as the other data updates. It runs at once
    when the jobs aren't triggered (development without Celery).
    Raise `SubmissionNotPending` if it's not waiting for approval any more.
    """
    with transaction.atomic():
        submission = lock_submission(submission, [SUBMISSION_STATUS_SUBMITTED])
        submission.status = SUBMISSION_STATUS_PUBLISHING
        submission.approved_by = user
        submission.publication_error = None
        submission.save()
        if app_settings.TRIGGER_JOBS:
            from tsosi.tasks import publish_submission as publish_task

            publish_task.delay_on_commit(submission.id, user.id)
    if not app_settings.TRIGGER_JOBS:
        run_publication(submission.id, user.id)


@transaction.atomic
def return_submission(submission: Submission) -> None:
    """
    Return a submission to the members: its declarations are drafts again,
    to be fixed and submitted again. They keep their submission until then.
    Raise `SubmissionNotPending` if it's not waiting for approval any more.
    """
    submission = lock_submission(submission, [SUBMISSION_STATUS_SUBMITTED])
    for declaration in submission.declarations.filter(
        status=DECLARATION_STATUS_SUBMITTED
    ):
        declaration.status = DECLARATION_STATUS_DRAFT
        declaration.save()
    submission.status = SUBMISSION_STATUS_RETURNED
    submission.save()


class _Rollback(Exception):
    pass


def simulate_publication(
    entity: Entity, read: Callable[[dict[int, Transfer | None], str], T]
) -> T:
    """
    Publish the organization's draft declarations, read the result with
    `read`, given the public transfer of each declaration and the hash of
    the drafts previewed (`drafts_hash`, checked by the submission), and
    roll it all back: the preview of the publication.
    """
    result = None
    supports = Transfer.objects.filter_by_entity(entity).filter(
        merged_into__isnull=True
    )
    converted = {
        t.id: (t.amount, t.currency_id, t.amounts_clc)
        for t in supports.filter(amounts_clc__isnull=False)
    }
    try:
        with transaction.atomic():
            declarations = load_declarations(
                Declaration.objects.filter(
                    entity=entity, status=DECLARATION_STATUS_DRAFT
                )
            )
            # Before the publication, which changes some of them
            declarations_hash = drafts_hash(declarations)
            data_load_source = create_data_load_source(
                entity, timezone.now(), "Hub preview"
            )
            results = apply_declarations(entity, declarations, data_load_source)
            # Computed by the enrichment tasks once published: the date, and
            # the converted amounts, kept when the amount didn't change
            for transfer in supports.filter(
                Q(date_clc__isnull=True) | Q(amounts_clc__isnull=True)
            ):
                if transfer.date_clc is None:
                    transfer.date_clc = get_date_clc(transfer)
                amount, currency, amounts = converted.get(
                    transfer.id, (None, None, None)
                )
                if (amount, currency) == (
                    transfer.amount,
                    transfer.currency_id,
                ):
                    transfer.amounts_clc = amounts
                transfer.save()
            result = read(results, declarations_hash)
            raise _Rollback
    except _Rollback:
        pass
    return result
