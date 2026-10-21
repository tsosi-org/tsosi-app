"""
Scenarios of the Data Contribution Hub across the data pipeline: the
publication followed by ingests, approvals run twice, and changes of the
members or entities while a submission waits.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

import tsosi.data.preparation.raw_data_config as dc
from tsosi.data.hub_publication import (
    SubmissionNotPending,
    approve_submission,
    publish_submission,
    return_submission,
    run_publication,
    submit_declarations,
)
from tsosi.data.ingestion.core import ingest
from tsosi.models import Currency, Declaration, Entity, Membership, Transfer
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_NEW,
    DECLARATION_STATUS_APPROVED,
    SUBMISSION_STATUS_APPROVED,
    SUBMISSION_STATUS_PUBLISHING,
    SUBMISSION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN
from tsosi.models.membership import MEMBERSHIP_STATUS_REVOKED
from tsosi.models.static_data import HUB_DATA_SOURCE

from .factories import DataLoadSourceFactory, EntityFactory, TransferFactory

ORG_NAME = "Université de Test"
INFRA_NAME = "Test Infrastructure"


@pytest.fixture(autouse=True)
def currency(db):
    Currency.objects.get_or_create(id="EUR")


def year(value: str) -> dict:
    return {"value": f"{value}-01-01", "precision": "year"}


def ingest_infra_data(amount=1000, data_source_id="doaj", date=None):
    """A full dataset of the infrastructure, with one support of the org."""
    source = dc.DataLoadSource(
        data_source_id=data_source_id,
        data_load_name="Test data",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    data = [
        {
            "emitter_name": ORG_NAME,
            "recipient_name": INFRA_NAME,
            "date_payment_recipient": date or year("2024"),
            "original_id": "1",
            "amount": amount,
            "currency": "EUR",
            "hide_amount": False,
        }
    ]
    config = dc.DataIngestionConfig(
        date_generated=datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
        source=source,
        count=len(data),
        data=data,
    )
    assert ingest(config, send_signals=False)


def member_of(entity: Entity, email="member@uni.edu"):
    user = get_user_model().objects.create_user(username=email, email=email)
    Membership.objects.create(user=user, entity=entity)
    return user


def public_supports(org: Entity) -> list[Transfer]:
    return list(Transfer.objects.filter(emitter=org, merged_into__isnull=True))


def approved(submission):
    """The submission, approved: being published (see `approve_submission`)."""
    submission.status = SUBMISSION_STATUS_PUBLISHING
    submission.save()
    return submission


def publish(org, member, admin_user):
    submission = submit_declarations(org, member)
    publish_submission(approved(submission), admin_user)
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_APPROVED
    return submission


@pytest.mark.django_db
def test_reingest_after_confirmation(registries, datasources, admin_user):
    """
    A full re-ingest of the infrastructure's data keeps the organization as
    a source of its confirmed support, with one public support.
    """
    ingest_infra_data()
    org = Entity.objects.get(name=ORG_NAME)
    member = member_of(org)
    [transfer] = public_supports(org)
    Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_CONFIRMATION,
        transfer=transfer,
    )
    publish(org, member, admin_user)

    ingest_infra_data()
    [transfer] = public_supports(org)
    assert transfer.recipient.scope == ENTITY_SCOPE_IN
    sources = {dls.data_source_id for dls in transfer.data_load_sources.all()}
    assert sources == {"doaj", HUB_DATA_SOURCE}


@pytest.mark.django_db
def test_reingest_corrected_after_confirmation(
    registries, datasources, admin_user
):
    """
    The infrastructure makes a support's date more precise after the
    organization confirmed it: the public support shows the new date, a
    confirmation doesn't freeze the values.
    """
    ingest_infra_data()
    org = Entity.objects.get(name=ORG_NAME)
    member = member_of(org)
    [transfer] = public_supports(org)
    Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_CONFIRMATION,
        transfer=transfer,
    )
    publish(org, member, admin_user)

    precise = {"value": "2024-05-10", "precision": "day"}
    ingest_infra_data(date=precise)
    [transfer] = public_supports(org)
    assert transfer.date_payment_recipient == precise
    sources = {d.data_source_id for d in transfer.data_load_sources.all()}
    assert sources == {"doaj", HUB_DATA_SOURCE}


@pytest.mark.django_db
@pytest.mark.xfail(
    strict=True,
    reason="Finding: a re-ingest after a Hub edit of the amount creates a "
    "duplicate (see the testing review)",
)
def test_reingest_after_amount_edit(registries, datasources, admin_user):
    """
    The organization corrects the amount of a support in the Hub, then the
    infrastructure's full dataset is ingested again, with its own amount:
    the support stays one, with the organization's amount.
    """
    ingest_infra_data(amount=1000)
    org = Entity.objects.get(name=ORG_NAME)
    infra = Entity.objects.get(name=INFRA_NAME)
    member = member_of(org)
    [transfer] = public_supports(org)
    Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_EDIT,
        transfer=transfer,
        recipient=infra,
        amount=1200,
        currency_id="EUR",
        date_payment_recipient=year("2024"),
    )
    publish(org, member, admin_user)
    [transfer] = public_supports(org)
    assert transfer.amount == 1200

    ingest_infra_data(amount=1000)
    supports = public_supports(org)
    assert [t.amount for t in supports] == [1200]


@pytest.mark.django_db
def test_reingest_after_agents_edit(registries, datasources, admin_user):
    """
    The organization adds the intermediary of a support in the Hub, then the
    infrastructure's dataset, without it, is ingested again: the support
    keeps the organization's intermediary.
    """
    ingest_infra_data()
    org = Entity.objects.get(name=ORG_NAME)
    infra = Entity.objects.get(name=INFRA_NAME)
    consortium = EntityFactory.create()
    member = member_of(org)
    [transfer] = public_supports(org)
    declaration = Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_EDIT,
        transfer=transfer,
        recipient=infra,
        amount=1000,
        currency_id="EUR",
        date_payment_recipient=year("2024"),
    )
    declaration.agents.set([consortium])
    publish(org, member, admin_user)

    ingest_infra_data()
    [transfer] = public_supports(org)
    assert list(transfer.agents.all()) == [consortium]
    sources = {d.data_source_id for d in transfer.data_load_sources.all()}
    assert sources == {"doaj", HUB_DATA_SOURCE}


@pytest.mark.django_db
def test_reingest_after_new_support(registries, datasources, admin_user):
    """
    A support declared in the Hub, then received in the infrastructure's
    data: the ingest merges them, the organization's values first.
    """
    ingest_infra_data()
    org = Entity.objects.get(name=ORG_NAME)
    infra = Entity.objects.get(name=INFRA_NAME)
    member = member_of(org)
    Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_NEW,
        recipient=infra,
        amount=800,
        currency_id="EUR",
        date_payment_recipient=year("2025"),
    )
    publish(org, member, admin_user)
    assert len(public_supports(org)) == 2

    # The infrastructure's new dataset has both supports
    source = dc.DataLoadSource(
        data_source_id="doaj",
        data_load_name="Test data",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    data = [
        {
            "emitter_name": ORG_NAME,
            "recipient_name": INFRA_NAME,
            "date_payment_recipient": year(date),
            "original_id": str(i),
            "amount": amount,
            "currency": "EUR",
            "hide_amount": False,
        }
        for i, (date, amount) in enumerate([("2024", 1000), ("2025", 800)])
    ]
    ingest(
        dc.DataIngestionConfig(
            date_generated="2025-01-01T00:00:00",
            source=source,
            count=2,
            data=data,
        ),
        send_signals=False,
    )
    supports = sorted(public_supports(org), key=lambda t: t.amount)
    assert [t.amount for t in supports] == [800, 1000]
    sources = {d.data_source_id for d in supports[0].data_load_sources.all()}
    assert sources == {"doaj", HUB_DATA_SOURCE}


@pytest.fixture
def org(db):
    return EntityFactory.create()


@pytest.fixture
def infra(db):
    return EntityFactory.create(scope=ENTITY_SCOPE_IN, is_recipient=True)


def new_support(org, member, infra) -> Declaration:
    return Declaration.objects.create(
        entity=org,
        author=member,
        kind=DECLARATION_KIND_NEW,
        recipient=infra,
        amount=500,
        currency_id="EUR",
        date_invoice=year("2025"),
    )


@pytest.mark.django_db
def test_publication_task_run_twice(org, infra, admin_user, datasources):
    """A task delivered twice publishes once."""
    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    submission.status = SUBMISSION_STATUS_PUBLISHING
    submission.save()
    run_publication(submission.id, admin_user.id)
    run_publication(submission.id, admin_user.id)
    assert len(public_supports(org)) == 1


@pytest.mark.django_db
def test_approve_stale_submission(
    org, infra, admin_user, datasources, settings
):
    """
    Two approvals of the same submission at once (a double click): the
    second one, which read the submission before the first one published
    it, publishes nothing.
    """
    settings.TSOSI_TRIGGER_JOBS = False
    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    stale = type(submission).objects.get(id=submission.id)
    approve_submission(submission, admin_user)
    assert len(public_supports(org)) == 1

    with pytest.raises(SubmissionNotPending):
        approve_submission(stale, admin_user)
    stale.refresh_from_db()
    assert stale.status == SUBMISSION_STATUS_APPROVED
    assert stale.data_load_source is not None
    assert len(public_supports(org)) == 1


@pytest.mark.django_db
def test_return_stale_submission(org, infra, admin_user, datasources):
    """
    A submission approved by another request can't be returned: its
    declarations stay approved, not drafts again.
    """
    member = member_of(org)
    declaration = new_support(org, member, infra)
    submission = submit_declarations(org, member)
    stale = type(submission).objects.get(id=submission.id)
    publish_submission(approved(submission), admin_user)

    with pytest.raises(SubmissionNotPending):
        return_submission(stale)
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_APPROVED


@pytest.mark.django_db
def test_returned_submission_not_published(org, infra, admin_user, datasources):
    """
    A returned submission isn't published: its declarations are drafts,
    which the members may be changing.
    """
    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    return_submission(submission)
    with pytest.raises(SubmissionNotPending):
        publish_submission(submission, admin_user)
    assert public_supports(org) == []


@pytest.mark.django_db
def test_submission_not_approved_not_published(
    org, infra, admin_user, datasources
):
    """
    Only an approved submission is published: not one waiting for approval,
    e.g. after a failed publication, by a late or redelivered task (C6).
    """
    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    with pytest.raises(SubmissionNotPending):
        publish_submission(submission, admin_user)
    assert public_supports(org) == []
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_SUBMITTED


@pytest.mark.django_db
def test_member_revoked_while_submitted(org, infra, admin_user, datasources):
    """
    The submission of a member revoked since is still published: it's the
    organization's data.
    """
    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    member.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    publish_submission(approved(submission), admin_user)
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_APPROVED
    assert submission.submitted_by == member
    assert len(public_supports(org)) == 1


@pytest.mark.django_db
def test_entities_merged_while_submitted(org, admin_user, datasources):
    """
    The beneficiary and intermediary of a declaration are merged into other
    entities while the submission waits: the support goes to those.
    """
    member = member_of(org)
    old_infra, infra = EntityFactory.create(), EntityFactory.create()
    old_agent, agent = EntityFactory.create(), EntityFactory.create()
    declaration = new_support(org, member, old_infra)
    declaration.agents.set([old_agent])
    submission = submit_declarations(org, member)
    for old, new in [(old_infra, infra), (old_agent, agent)]:
        old.merged_with = new
        old.merged_criteria = "test"
        old.is_active = False
        old.save()

    publish_submission(approved(submission), admin_user)
    [transfer] = public_supports(org)
    assert transfer.recipient == infra
    assert list(transfer.agents.all()) == [agent]
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_APPROVED


@pytest.mark.django_db
def test_two_members_change_the_same_support(org, infra, datasources):
    """
    Two members of the organization change the same support: the second
    one is told that it already has a change, without an error 500.
    """
    transfer = TransferFactory.create(
        emitter=org,
        recipient=infra,
        currency_id="EUR",
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id="doaj", entity=infra)
        ],
    )
    url = f"/api/hub/entities/{org.id}/declarations"
    responses = []
    for email in ["one@uni.edu", "two@uni.edu"]:
        client = APIClient()
        client.force_login(member_of(org, email))
        responses.append(
            client.post(
                url,
                {"kind": "confirmation", "transfer_id": str(transfer.id)},
                format="json",
            )
        )
    assert [r.status_code for r in responses] == [201, 400]
    assert "already has a change" in str(responses[1].json())


def org_support(org, infra, declarer=None) -> Transfer:
    return TransferFactory.create(
        emitter=org,
        recipient=infra,
        currency_id="EUR",
        data_load_sources=[
            DataLoadSourceFactory.create(
                data_source_id="doaj", entity=declarer or infra
            )
        ],
    )


def delete(org, transfer, other):
    transfer.delete()


def merge_by_ingest(org, transfer, other):
    transfer.merged_into = other
    transfer.save()


def declared_since(org, transfer, other):
    transfer.data_load_sources.add(
        DataLoadSourceFactory.create(data_source_id="rennes", entity=org)
    )


def not_declared_any_more(org, transfer, other):
    transfer.data_load_sources.remove(
        *transfer.data_load_sources.filter(entity=org)
    )


def delete_other(org, transfer, other):
    other.delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind, org_is_source, change, conflict",
    [
        ("confirmation", False, delete, "deleted since the submission"),
        ("confirmation", False, merge_by_ingest, "changed since"),
        ("confirmation", False, declared_since, "declared this support"),
        ("removal", True, not_declared_any_more, "isn't a source"),
        ("merge", False, delete_other, "deleted since the submission"),
        ("not_duplicate", False, merge_by_ingest, "changed since"),
    ],
)
def test_publication_conflicts(
    org, infra, admin_user, datasources, kind, org_is_source, change, conflict
):
    """
    The data changed since the submission, e.g. by an ingest: nothing is
    published, the submission waits with the conflict.
    """
    member = member_of(org)
    transfer = org_support(org, infra, org if org_is_source else infra)
    other = org_support(org, infra)
    declaration = Declaration.objects.create(
        entity=org, author=member, kind=kind, transfer=transfer
    )
    if kind in ["merge", "not_duplicate"]:
        declaration.other_transfers.set([other])
    submission = submit_declarations(org, member)
    change(org, transfer, other)

    submission.status = SUBMISSION_STATUS_PUBLISHING
    submission.save()
    run_publication(submission.id, admin_user.id)
    submission.refresh_from_db()
    assert submission.status == "submitted"
    assert conflict in submission.publication_error
    assert not Transfer.objects.filter(
        data_load_sources__data_source_id=HUB_DATA_SOURCE
    ).exists()


@pytest.mark.django_db
def test_publication_unexpected_error(
    org, infra, admin_user, datasources, monkeypatch
):
    """
    An unexpected error: nothing is published, the submission waits for
    approval again, and the error reaches the task's logs.
    """
    from tsosi.data import hub_publication

    member = member_of(org)
    new_support(org, member, infra)
    submission = submit_declarations(org, member)
    submission.status = SUBMISSION_STATUS_PUBLISHING
    submission.save()

    def fail(*args):
        raise RuntimeError("Unexpected")

    monkeypatch.setattr(hub_publication, "apply_declarations", fail)
    with pytest.raises(RuntimeError):
        run_publication(submission.id, admin_user.id)
    submission.refresh_from_db()
    assert submission.status == "submitted"
    assert "unexpected error" in submission.publication_error
    assert public_supports(org) == []
