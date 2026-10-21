import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tsosi.data.hub_publication import (
    PublicationConflict,
    approve_submission,
    drafts_hash,
    load_declarations,
    publish_submission,
    run_publication,
    submit_declarations,
)
from tsosi.data.signals import transfers_created
from tsosi.models import (
    Currency,
    DataLoadSource,
    Declaration,
    Membership,
    Transfer,
)
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_STATUS_APPROVED,
    DECLARATION_STATUS_DRAFT,
    DECLARATION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_APPROVED,
    SUBMISSION_STATUS_PUBLISHING,
    SUBMISSION_STATUS_RETURNED,
    SUBMISSION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK
from tsosi.models.static_data import HUB_DATA_SOURCE

from .factories import DataLoadSourceFactory, EntityFactory, TransferFactory


@pytest.fixture(autouse=True)
def currency(db):
    Currency.objects.get_or_create(id="EUR")


@pytest.fixture
def org(db):
    return EntityFactory.create()


@pytest.fixture
def member(org):
    user = get_user_model().objects.create_user(
        username="member@uni.edu", email="member@uni.edu"
    )
    Membership.objects.create(user=user, entity=org)
    return user


@pytest.fixture
def client(member) -> APIClient:
    client = APIClient()
    client.force_login(member)
    return client


@pytest.fixture
def infra(db):
    return EntityFactory.create(scope=ENTITY_SCOPE_IN, is_recipient=True)


def year(value: str) -> dict:
    return {"value": f"{value}-01-01", "precision": "year"}


def support(org, infra, declarer, amount=1000, date="2024", source="doaj"):
    """A support of the organization, declared by `declarer`."""
    return TransferFactory.create(
        emitter=org,
        recipient=infra,
        amount=amount,
        currency_id="EUR",
        date_invoice=None,
        date_payment_emitter=None,
        date_payment_recipient=year(date),
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id=source, entity=declarer)
        ],
    )


def declare(org, member, kind, transfer=None, others=(), **values):
    declaration = Declaration.objects.create(
        entity=org, author=member, kind=kind, transfer=transfer, **values
    )
    declaration.other_transfers.set(others)
    return declaration


def new_values(infra, amount=500, **values) -> dict:
    return {
        "recipient": infra,
        "amount": amount,
        "currency_id": "EUR",
        "date_invoice": year("2025"),
        **values,
    }


def approved(submission):
    """The submission, approved: being published (see `approve_submission`)."""
    submission.status = SUBMISSION_STATUS_PUBLISHING
    submission.save()
    return submission


def publish(org, member, admin_user):
    submission = submit_declarations(org, member)
    publish_submission(approved(submission), admin_user)
    submission.refresh_from_db()
    return submission


def sources(transfer: Transfer) -> list[Transfer]:
    return list(transfer.merged_transfers.all()) or [transfer]


def hub_source(transfer: Transfer) -> Transfer:
    return next(
        s
        for s in sources(transfer)
        if s.data_load_sources.filter(data_source_id=HUB_DATA_SOURCE).exists()
    )


@pytest.mark.django_db
def test_publish_new(org, member, admin_user, datasources):
    new_infra = EntityFactory.create()
    consortium = EntityFactory.create()
    declaration = declare(
        org, member, DECLARATION_KIND_NEW, **new_values(new_infra)
    )
    declaration.agents.set([consortium])
    signals = []
    transfers_created.connect(receiver := lambda **kw: signals.append(kw))
    try:
        submission = publish(org, member, admin_user)
    finally:
        transfers_created.disconnect(receiver)

    assert submission.status == SUBMISSION_STATUS_APPROVED
    assert submission.approved_by == admin_user
    dls = submission.data_load_source
    assert dls.data_source_id == HUB_DATA_SOURCE
    assert dls.entity == org and not dls.full_data
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_APPROVED
    transfer = declaration.published_transfer
    # A support of its own, standing alone
    assert transfer.merged_into is None
    assert transfer.emitter == org and transfer.recipient == new_infra
    assert transfer.amount == 500 and transfer.currency_id == "EUR"
    assert transfer.date_invoice == year("2025")
    assert list(transfer.agents.all()) == [consortium]
    assert list(transfer.data_load_sources.all()) == [dls]
    # A beneficiary without scope is to be checked
    new_infra.refresh_from_db()
    assert new_infra.scope == ENTITY_SCOPE_TO_CHECK
    # The enrichment is triggered
    assert len(signals) == 1


@pytest.mark.django_db
def test_publish_confirmation(org, member, admin_user, infra, datasources):
    transfer = support(org, infra, infra)
    declaration = declare(org, member, DECLARATION_KIND_CONFIRMATION, transfer)
    publish(org, member, admin_user)

    transfer.refresh_from_db()
    # The same public transfer, with the organization as a source
    assert transfer.merged_into is None
    assert len(sources(transfer)) == 2
    assert transfer.data_load_sources.filter(entity=org).exists()
    assert transfer.amount == 1000
    declaration.refresh_from_db()
    assert declaration.published_transfer == hub_source(transfer)
    # The other sources' values still apply
    assert not hub_source(transfer).hub_values
    assert declaration.transfer == transfer


@pytest.mark.django_db
def test_publish_edit(org, member, admin_user, infra, datasources):
    declared_by_infra = support(org, infra, infra)
    declared_by_org = support(org, infra, org, date="2023", source="rennes")
    previous_dls = declared_by_org.data_load_sources.get()
    declare(
        org,
        member,
        DECLARATION_KIND_EDIT,
        declared_by_infra,
        **new_values(infra, amount=1200, date_payment_recipient=year("2024")),
    )
    declare(
        org,
        member,
        DECLARATION_KIND_EDIT,
        declared_by_org,
        **new_values(infra, amount=800, date_payment_recipient=year("2023")),
    )
    submission = publish(org, member, admin_user)

    # The organization's values win over the other source's
    declared_by_infra.refresh_from_db()
    assert declared_by_infra.amount == 1200
    assert declared_by_infra.date_invoice == year("2025")
    other = next(s for s in sources(declared_by_infra) if s.amount == 1000)
    assert other.data_load_sources.get().entity == infra

    # Its previous source transfer is updated, its old values in the history
    declared_by_org.refresh_from_db()
    assert declared_by_org.merged_into is None
    assert declared_by_org.amount == 800
    assert declared_by_org.hub_values
    assert hub_source(declared_by_infra).hub_values
    assert list(declared_by_org.data_load_sources.all()) == [
        submission.data_load_source
    ]
    assert declared_by_org.history.filter(amount=1000).exists()
    assert declared_by_org.history.latest().history_user is None
    assert DataLoadSource.objects.filter(id=previous_dls.id).exists()


@pytest.mark.django_db
def test_publish_removal(org, member, admin_user, infra, datasources):
    only_org = support(org, infra, org, source="rennes")
    with_infra = support(org, infra, infra, date="2023")
    # Confirmed by the organization
    declare(org, member, DECLARATION_KIND_CONFIRMATION, with_infra)
    publish(org, member, admin_user)
    with_infra.refresh_from_db()
    assert len(sources(with_infra)) == 2

    removals = [
        declare(org, member, DECLARATION_KIND_REMOVAL, t)
        for t in [only_org, with_infra]
    ]
    publish(org, member, admin_user)
    # Deleted without other source
    assert not Transfer.objects.filter(id=only_org.id).exists()
    # Else computed again from the remaining one, with its ID
    with_infra.refresh_from_db()
    assert with_infra.merged_into is None
    assert not with_infra.data_load_sources.filter(entity=org).exists()
    assert [s.data_load_sources.get().entity for s in sources(with_infra)] == [
        infra
    ]
    # The declarations keep a trace
    for declaration in removals:
        declaration.refresh_from_db()
        assert declaration.status == DECLARATION_STATUS_APPROVED
    assert removals[0].transfer is None
    assert removals[1].transfer == with_infra


@pytest.mark.django_db
def test_publish_merge(org, member, admin_user, infra, datasources):
    consortium = EntityFactory.create()
    first = support(org, infra, infra)
    second = support(org, infra, consortium, amount=1100, source="couperin")
    second_id = second.id
    declare(org, member, DECLARATION_KIND_MERGE, first, [second])
    # And confirmed in the same submission
    declare(org, member, DECLARATION_KIND_CONFIRMATION, second)
    publish(org, member, admin_user)

    public = Transfer.objects.filter(
        merged_into__isnull=True, emitter=org, recipient=infra
    )
    assert public.count() == 1
    merged = public.get()
    # The older one keeps its ID
    assert merged.id == first.id
    assert {s.data_load_sources.get().entity_id for s in sources(merged)} == {
        infra.id,
        consortium.id,
        org.id,
    }
    # Kept as a source
    assert Transfer.objects.get(id=second_id).merged_into == merged


@pytest.mark.django_db
def test_publish_not_duplicate(
    client, org, member, admin_user, infra, datasources
):
    first = support(org, infra, infra)
    second = support(org, infra, infra, amount=1100)
    url = f"/api/hub/entities/{org.id}/declarations"
    pairs = client.get(url).json()["possible_duplicates"]
    assert [set(p) for p in pairs] == [{str(first.id), str(second.id)}]
    declaration = declare(
        org, member, DECLARATION_KIND_NOT_DUPLICATE, first, [second]
    )
    # Not flagged once reconciled, already while pending
    assert client.get(url).json()["possible_duplicates"] == []
    publish(org, member, admin_user)

    # Nothing published, the pair isn't flagged any more
    assert Transfer.objects.filter(merged_into__isnull=True).count() == 2
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_APPROVED
    assert declaration.published_transfer is None
    assert client.get(url).json()["possible_duplicates"] == []


@pytest.mark.django_db
def test_publication_conflict(org, member, admin_user, infra, datasources):
    confirmed = support(org, infra, infra)
    declare(org, member, DECLARATION_KIND_CONFIRMATION, confirmed)
    declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    submission = submit_declarations(org, member)
    # Published data changed since: an ingest corrected the amount, and
    # brought a support that may be the new one
    confirmed.amount = 1500
    confirmed.save()
    support(org, infra, infra, amount=600, date="2025")

    with pytest.raises(PublicationConflict) as error:
        publish_submission(approved(submission), admin_user)
    assert len(error.value.conflicts) == 2
    assert "changed since the submission" in error.value.conflicts[0]
    assert "may be the same" in error.value.conflicts[1]
    # Nothing published
    assert not DataLoadSource.objects.filter(
        data_source_id=HUB_DATA_SOURCE
    ).exists()
    assert len(sources(confirmed)) == 1

    # The approval shows the conflicts, the submission waits again
    run_publication(submission.id, admin_user.id)
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_SUBMITTED
    assert "changed since the submission" in submission.publication_error
    assert set(submission.declarations.values_list("status", flat=True)) == {
        DECLARATION_STATUS_SUBMITTED
    }


def submissions_url(entity) -> str:
    return f"/api/hub/entities/{entity.id}/submissions"


def previewed(client, entity) -> dict:
    """The submission of the drafts that the preview shows."""
    preview = client.get(f"/api/hub/entities/{entity.id}/publication-preview")
    assert preview.status_code == 200, preview.json()
    return {
        "consent": True,
        "declaration_ids": preview.json()["declaration_ids"],
        "declarations_hash": preview.json()["declarations_hash"],
    }


@pytest.mark.django_db
def test_submit(client, org, member, admin_user, infra, datasources):
    transfer = support(org, infra, infra)
    declaration = declare(org, member, DECLARATION_KIND_CONFIRMATION, transfer)
    payload = previewed(client, org)
    assert payload["declaration_ids"] == [declaration.id]
    response = client.post(
        submissions_url(org), {**payload, "consent": False}, format="json"
    )
    assert "consent" in response.json()
    # The changes previewed are required
    response = client.post(submissions_url(org), {"consent": True})
    assert "declaration_ids" in response.json()
    assert "declarations_hash" in response.json()
    response = client.post(submissions_url(org), payload, format="json")
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["changes_count"] == 1
    assert data["submitted_by"] == member.email
    assert data["status"] == SUBMISSION_STATUS_SUBMITTED

    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_SUBMITTED
    submission = declaration.submission
    assert submission.consent_at is not None
    # The published values it relies on
    snapshot = submission.snapshot[str(declaration.id)]
    assert snapshot["transfer"]["id"] == str(transfer.id)
    assert snapshot["transfer"]["amount"] == 1000
    # Read-only, and nothing else to submit
    url = f"/api/hub/entities/{org.id}/declarations/{declaration.id}"
    assert client.delete(url).status_code == 403
    response = client.post(
        submissions_url(org), previewed(client, org), format="json"
    )
    assert response.status_code == 400
    assert "no changes to submit" in str(response.json())

    # Listed while waiting for approval, to the TSOSI team too
    assert [s["id"] for s in client.get(submissions_url(org)).json()] == [
        submission.id
    ]
    staff = APIClient()
    staff.force_login(admin_user)
    assert len(staff.get(submissions_url(org)).json()) == 1
    # Which can't submit
    response = staff.post(submissions_url(org), payload, format="json")
    assert response.status_code == 403
    other = EntityFactory.create()
    assert client.get(submissions_url(other)).status_code == 404


@pytest.mark.django_db
def test_submit_previewed_changes_only(client, org, member, infra, datasources):
    """
    The consent is for the changes previewed: a draft added or undone since,
    e.g. by another member, makes the submission fail, nothing submitted.
    """
    transfer = support(org, infra, infra)
    first = declare(org, member, DECLARATION_KIND_CONFIRMATION, transfer)
    payload = previewed(client, org)
    assert payload["declaration_ids"] == [first.id]
    # Added in another tab
    added = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    response = client.post(submissions_url(org), payload, format="json")
    assert response.status_code == 400
    assert "changed since the preview" in response.json()["detail"]
    assert not first.__class__.objects.filter(submission__isnull=False).exists()
    # Undone, it's the previewed one only again
    added.delete()
    response = client.post(submissions_url(org), payload, format="json")
    assert response.status_code == 201, response.json()


@pytest.mark.django_db
def test_submit_previewed_values_only(client, org, member, infra, datasources):
    """
    A draft edited since the preview, e.g. by another member, makes the
    submission fail, though the drafts are the same (C2).
    """
    edited = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    payload = previewed(client, org)
    assert payload["declaration_ids"] == [edited.id]
    # The preview gives the same hash again
    assert previewed(client, org) == payload
    url = f"/api/hub/entities/{org.id}/declarations/{edited.id}"
    response = client.put(
        url,
        {
            "kind": DECLARATION_KIND_NEW,
            "recipient_id": str(infra.id),
            "amount": 5000,
            "currency": "EUR",
            "date_invoice": "2025",
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    response = client.post(submissions_url(org), payload, format="json")
    assert response.status_code == 400
    assert "changed since the preview" in response.json()["detail"]
    assert not Declaration.objects.filter(submission__isnull=False).exists()
    # Previewed again, it's submitted with the new amount
    payload = previewed(client, org)
    response = client.post(submissions_url(org), payload, format="json")
    assert response.status_code == 201, response.json()
    edited.refresh_from_db()
    assert edited.status == DECLARATION_STATUS_SUBMITTED
    assert edited.amount == 5000


@pytest.mark.django_db
def test_drafts_hash(org, member, infra, datasources):
    """The hash changes with every value submitted, in any order."""
    transfer = support(org, infra, infra)
    new = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    other = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    confirmation = declare(org, member, DECLARATION_KIND_CONFIRMATION, transfer)

    def current_hash(declarations=None):
        return drafts_hash(
            load_declarations(
                Declaration.objects.filter(
                    id__in=[d.id for d in declarations or [new, other]]
                )
            )
        )

    initial = current_hash()
    assert len(initial) == 64
    assert current_hash() == initial
    assert drafts_hash([other, new]) == drafts_hash([new, other])
    hashes = {initial, current_hash([new, other, confirmation])}
    changes = [
        lambda: Declaration.objects.filter(id=new.id).update(amount=501),
        lambda: Declaration.objects.filter(id=new.id).update(
            date_invoice=year("2024")
        ),
        lambda: Declaration.objects.filter(id=new.id).update(
            recipient=EntityFactory.create()
        ),
        lambda: new.agents.set([EntityFactory.create()]),
        lambda: new.other_transfers.set([transfer]),
        lambda: new.other_declarations.set([other]),
        lambda: Declaration.objects.filter(id=new.id).update(
            kind=DECLARATION_KIND_EDIT,
            transfer=support(org, infra, infra, date="2023"),
        ),
    ]
    for change in changes:
        change()
        hashes.add(current_hash())
    assert len(hashes) == len(changes) + 2


@pytest.mark.django_db
def test_publication_preview(client, org, member, infra, datasources):
    confirmed = support(org, infra, infra)
    removed = support(org, infra, org, date="2023", source="rennes")
    declare(org, member, DECLARATION_KIND_CONFIRMATION, confirmed)
    declare(org, member, DECLARATION_KIND_REMOVAL, removed)
    new = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    transfers_count = Transfer.objects.count()

    response = client.get(f"/api/hub/entities/{org.id}/publication-preview")
    assert response.status_code == 200, response.json()
    data = response.json()
    transfers = {t["id"]: t for t in data["transfers"]}
    assert str(removed.id) not in transfers
    assert data["changes"][str(confirmed.id)] == [DECLARATION_KIND_CONFIRMATION]
    assert not transfers[str(confirmed.id)]["unconverted"]
    (new_id,) = [i for i, c in data["changes"].items() if c == ["new"]]
    # Not converted nor dated by the enrichment yet
    assert transfers[new_id]["unconverted"]
    assert transfers[new_id]["amounts_clc"] == {"EUR": 500}
    assert transfers[new_id]["date_clc"] == year("2025")

    # Nothing saved
    assert Transfer.objects.count() == transfers_count
    assert not Transfer.objects.filter(id=new_id).exists()
    assert not DataLoadSource.objects.filter(
        data_source_id=HUB_DATA_SOURCE
    ).exists()
    new.refresh_from_db()
    assert new.status == DECLARATION_STATUS_DRAFT


@pytest.mark.django_db
def test_publication_preview_hidden_amounts(
    client, org, member, infra, datasources
):
    """
    Hidden amounts are left out of the preview, as on the public page: those
    of the supports of the organization's children too (F23).
    """
    child = EntityFactory.create()
    child.parents.add(org)
    converted = support(child, infra, infra)
    unconverted = support(child, infra, infra, date="2023")
    shown = support(child, infra, infra, date="2022")
    Transfer.objects.filter(id__in=[converted.id, unconverted.id]).update(
        hide_amount=True
    )
    Transfer.objects.filter(id=unconverted.id).update(amounts_clc=None)
    declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))

    response = client.get(f"/api/hub/entities/{org.id}/publication-preview")
    assert response.status_code == 200, response.json()
    transfers = {t["id"]: t for t in response.json()["transfers"]}
    for transfer in (converted, unconverted):
        values = transfers[str(transfer.id)]
        assert values["amount_hidden"]
        assert not values["unconverted"]
        assert values["amount"] is None
        assert values["currency"] is None
        assert values["amounts_clc"] is None
    assert transfers[str(shown.id)]["amount"] == shown.amount
    assert transfers[str(shown.id)]["currency"] == "EUR"


SUBMISSION_ADMIN_URL = "/admin/tsosi/submission/"


@pytest.mark.django_db
def test_admin_approve(
    admin_client, admin_user, org, member, infra, datasources, settings
):
    new_infra = EntityFactory.create()
    new_infra.added_in_hub_by.add(org)
    declare(org, member, DECLARATION_KIND_NEW, **new_values(new_infra))
    submission = submit_declarations(org, member)

    response = admin_client.get(SUBMISSION_ADMIN_URL)
    assert response.status_code == 200
    assert "1 new support" in response.content.decode()
    # The organization's submissions, linked from its page
    entity_page = admin_client.get(f"/admin/tsosi/entity/{org.id}/change/")
    assert f"?entity__id__exact={org.id}" in entity_page.content.decode()
    response = admin_client.get(
        SUBMISSION_ADMIN_URL, {"entity__id__exact": org.id}
    )
    assert list(response.context["cl"].result_list) == [submission]
    # And those using the infrastructure it added
    entity_page = admin_client.get(
        f"/admin/tsosi/entity/{new_infra.id}/change/"
    )
    assert f"/admin/tsosi/submission/{submission.id}/change/" in (
        entity_page.content.decode()
    )
    url = f"{SUBMISSION_ADMIN_URL}{submission.id}/change/"
    content = admin_client.get(url).content.decode()
    assert "Approve and publish" in content
    # The organizations added in the Hub, to check
    assert new_infra.name in content
    assert "no scope: to be checked" in content

    approve_url = f"{SUBMISSION_ADMIN_URL}{submission.id}/approve/"
    assert admin_client.get(approve_url).status_code == 405
    # Published at once without the Celery jobs
    settings.TSOSI_TRIGGER_JOBS = False
    response = admin_client.post(approve_url)
    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_APPROVED
    assert submission.approved_by == admin_user
    transfer = submission.declarations.get().published_transfer
    # Recorded with the admin user
    assert transfer.history.latest().history_user == admin_user
    # Not twice: a double click gets the "not pending" message (C9)
    response = admin_client.post(approve_url, follow=True)
    assert response.redirect_chain == [(url, 302)]
    assert "approved or returned meanwhile" in response.content.decode()
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_APPROVED
    assert (
        DataLoadSource.objects.filter(data_source_id=HUB_DATA_SOURCE).count()
        == 1
    )
    # Nor returned once approved
    response = admin_client.post(
        f"{SUBMISSION_ADMIN_URL}{submission.id}/return/", follow=True
    )
    assert "approved or returned meanwhile" in response.content.decode()
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_APPROVED
    # An unknown submission is still a 404
    unknown_url = f"{SUBMISSION_ADMIN_URL}{submission.id + 1}/approve/"
    assert admin_client.post(unknown_url).status_code == 404


@pytest.mark.django_db
def test_admin_approve_task(
    admin_user, org, member, infra, datasources, monkeypatch
):
    from tsosi import tasks

    queued = []
    monkeypatch.setattr(
        tasks.publish_submission,
        "delay_on_commit",
        lambda *args: queued.append(args),
    )
    declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    submission = submit_declarations(org, member)
    approve_submission(submission, admin_user)
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_PUBLISHING
    assert queued == [(submission.id, admin_user.id)]


@pytest.mark.django_db
def test_admin_return(admin_client, client, org, member, infra, datasources):
    transfer = support(org, infra, infra)
    declaration = declare(org, member, DECLARATION_KIND_CONFIRMATION, transfer)
    submission = submit_declarations(org, member)
    response = admin_client.post(
        f"{SUBMISSION_ADMIN_URL}{submission.id}/return/"
    )
    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == SUBMISSION_STATUS_RETURNED
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_DRAFT
    # Members can change it again
    url = f"/api/hub/entities/{org.id}/declarations/{declaration.id}"
    assert client.delete(url).status_code == 204
