import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from rest_framework.test import APIClient

from tsosi.data.hub_publication import submit_declarations
from tsosi.models import Currency, Declaration, Membership
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_STATUS_APPROVED,
    DECLARATION_STATUS_DRAFT,
    DECLARATION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK

from .factories import DataLoadSourceFactory, EntityFactory, TransferFactory


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


@pytest.fixture
def supports(org, infra, datasources):
    """
    A transfer declared by the infrastructure only, and one declared by the
    organization too.
    """
    Currency.objects.get_or_create(id="EUR")
    declared_by_infra = TransferFactory.create(
        emitter=org,
        recipient=infra,
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id="doaj", entity=infra)
        ],
    )
    declared_by_org = TransferFactory.create(
        emitter=org,
        recipient=infra,
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id="rennes", entity=org)
        ],
    )
    return declared_by_infra, declared_by_org


def url(entity, declaration=None) -> str:
    base = f"/api/hub/entities/{entity.id}/declarations"
    return f"{base}/{declaration.id}" if declaration else base


def new_support(infra, **values) -> dict:
    return {
        "kind": DECLARATION_KIND_NEW,
        "recipient_id": str(infra.id),
        "amount": 1500,
        "currency": "EUR",
        "date_invoice": "2024-03",
        **values,
    }


@pytest.mark.django_db
def test_new_support(client, member, org, infra, supports):
    agent = EntityFactory.create()
    response = client.post(
        url(org),
        new_support(
            infra,
            agent_ids=[str(agent.id)],
            date_start="2024",
            date_end="2024-12-31",
        ),
        format="json",
    )
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["kind"] == DECLARATION_KIND_NEW
    assert data["status"] == DECLARATION_STATUS_DRAFT
    assert data["transfer_id"] is None
    assert data["agent_ids"] == [str(agent.id)]
    assert data["author"] == member.email
    # The precision comes from what is typed
    assert data["date_invoice"] == {"value": "2024-03-01", "precision": "month"}
    assert data["date_start"] == {"value": "2024-01-01", "precision": "year"}
    assert data["date_payment_emitter"] is None

    declaration = Declaration.objects.get(id=data["id"])
    assert declaration.entity == org
    # Every change is recorded with its user
    assert {h.history_user for h in declaration.history.all()} == {member}

    response = client.get(url(org))
    assert [d["id"] for d in response.json()["declarations"]] == [data["id"]]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "values, field",
    [
        ({"recipient_id": None}, "recipient_id"),
        ({"date_invoice": None}, "dates"),
        ({"date_invoice": "2024-13"}, "date_invoice"),
        ({"date_invoice": "24"}, "date_invoice"),
        ({"date_invoice": "2023-02-29"}, "date_invoice"),
        ({"date_start": "2024"}, "date_end"),
        ({"date_start": "2024-06", "date_end": "2024-01"}, "date_end"),
        ({"date_start": "2024-06-15", "date_end": "2024-05"}, "date_end"),
        ({"date_start": "2024", "date_end": "2023-12-31"}, "date_end"),
        ({"amount": -10}, "amount"),
        # Saved, they would break every response, not JSON compliant
        ({"amount": "NaN"}, "amount"),
        ({"amount": "Infinity"}, "amount"),
        ({"amount": "1e400"}, "amount"),
        ({"currency": None}, "currency"),
        ({"amount": None}, "amount"),
        ({"currency": "XYZ"}, "currency"),
    ],
)
def test_new_support_validation(client, org, infra, values, field):
    Currency.objects.get_or_create(id="EUR")
    response = client.post(
        url(org), new_support(infra, **values), format="json"
    )
    assert response.status_code == 400
    assert field in response.json()
    assert not Declaration.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "start, end",
    [("2024", "2024"), ("2024-06", "2024"), ("2024-06-15", "2024-06")],
)
def test_agreement_dates_of_other_precisions(client, org, infra, start, end):
    """The dates are compared at the coarser precision of the two."""
    Currency.objects.get_or_create(id="EUR")
    response = client.post(
        url(org),
        new_support(infra, date_start=start, date_end=end),
        format="json",
    )
    assert response.status_code == 201, response.json()


@pytest.mark.django_db
def test_new_support_amount_required(client, org, infra):
    Currency.objects.get_or_create(id="EUR")
    response = client.post(
        url(org),
        new_support(infra, amount=None, currency=None),
        format="json",
    )
    assert response.status_code == 400
    assert set(response.json()) == {"amount", "currency"}

    response = client.post(
        url(org),
        new_support(infra, date_invoice=None)
        | {"date_payment_recipient": "2024-03-13"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["date_payment_recipient"]["precision"] == "day"


@pytest.mark.django_db
def test_confirm_and_remove(client, org, infra, supports):
    declared_by_infra, declared_by_org = supports
    # A new support doesn't refer to a transfer
    response = client.post(
        url(org),
        new_support(infra, transfer_id=str(declared_by_infra.id)),
        format="json",
    )
    assert response.status_code == 400

    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_CONFIRMATION,
            "transfer_id": str(declared_by_infra.id),
            # Ignored: only the transfer's values are published
            "amount": 12,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["amount"] is None
    # One pending change per support
    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_EDIT,
            "transfer_id": str(declared_by_infra.id),
        }
        | new_support(infra, kind=DECLARATION_KIND_EDIT),
        format="json",
    )
    assert "already has a change not published yet" in str(response.json())

    # Already declared by the organization
    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_CONFIRMATION,
            "transfer_id": str(declared_by_org.id),
        },
        format="json",
    )
    assert "already declared" in str(response.json())

    # Only the organization's own declarations can be removed
    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_REMOVAL,
            "transfer_id": str(declared_by_org.id),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    Declaration.objects.all().delete()
    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_REMOVAL,
            "transfer_id": str(declared_by_infra.id),
        },
        format="json",
    )
    assert "Only the supports that the organization declared" in str(
        response.json()
    )

    # Another organization's support, a child's included: it's listed in the
    # organization's table, read-only
    child = EntityFactory.create()
    child.parents.add(org)
    for other in [
        TransferFactory.create(recipient=infra),
        TransferFactory.create(emitter=child, recipient=infra),
    ]:
        response = client.post(
            url(org),
            {
                "kind": DECLARATION_KIND_CONFIRMATION,
                "transfer_id": str(other.id),
            },
            format="json",
        )
        assert "Only the organization's own supports" in str(response.json())


@pytest.mark.django_db
def test_edit_draft(client, org, infra, supports):
    declared_by_infra, _ = supports
    response = client.post(
        url(org),
        {
            "kind": DECLARATION_KIND_CONFIRMATION,
            "transfer_id": str(declared_by_infra.id),
        },
        format="json",
    )
    declaration = Declaration.objects.get(id=response.json()["id"])

    # The confirmation becomes an edit
    response = client.put(
        url(org, declaration),
        new_support(infra, kind=DECLARATION_KIND_EDIT),
        format="json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["kind"] == DECLARATION_KIND_EDIT
    assert response.json()["transfer_id"] == str(declared_by_infra.id)
    assert response.json()["amount"] == 1500
    # Validated as on creation
    response = client.put(
        url(org, declaration),
        new_support(infra, kind=DECLARATION_KIND_EDIT, recipient_id=None),
        format="json",
    )
    assert response.status_code == 400
    # The transfer doesn't change
    other = TransferFactory.create(emitter=org, recipient=infra)
    response = client.put(
        url(org, declaration),
        new_support(
            infra, kind=DECLARATION_KIND_EDIT, transfer_id=str(other.id)
        ),
        format="json",
    )
    assert "transfer_id" in response.json()
    # Nor can it become a new support
    response = client.put(
        url(org, declaration), new_support(infra), format="json"
    )
    assert response.status_code == 400

    # Undo
    assert client.delete(url(org, declaration)).status_code == 204
    assert not Declaration.objects.exists()


@pytest.mark.django_db
def test_submitted_declarations(client, org, infra, supports):
    declared_by_infra, declared_by_org = supports
    submitted = Declaration.objects.create(
        entity=org,
        kind=DECLARATION_KIND_CONFIRMATION,
        transfer=declared_by_infra,
        status=DECLARATION_STATUS_SUBMITTED,
    )
    approved = Declaration.objects.create(
        entity=org,
        kind=DECLARATION_KIND_REMOVAL,
        transfer=declared_by_org,
        status=DECLARATION_STATUS_APPROVED,
    )
    # Read-only
    assert client.delete(url(org, submitted)).status_code == 403
    response = client.put(
        url(org, submitted),
        new_support(infra, kind=DECLARATION_KIND_EDIT),
        format="json",
    )
    assert response.status_code == 403
    # Still pending: no other change on the same support
    response = client.post(
        url(org),
        new_support(
            infra,
            kind=DECLARATION_KIND_EDIT,
            transfer_id=str(declared_by_infra.id),
        ),
        format="json",
    )
    assert "already has a change not published yet" in str(response.json())
    # Approved declarations aren't listed
    ids = [d["id"] for d in client.get(url(org)).json()["declarations"]]
    assert ids == [submitted.id]
    assert approved.id not in ids


@pytest.mark.django_db
def test_change_submitted_draft(client, org, member, infra, supports):
    """
    A draft submitted by another member in the meantime can't be changed nor
    deleted: it stays in its submission (C5).
    """
    response = client.post(url(org), new_support(infra), format="json")
    declaration = Declaration.objects.get(id=response.json()["id"])
    submission = submit_declarations(org, member)
    response = client.put(
        url(org, declaration), new_support(infra, amount=10), format="json"
    )
    assert response.status_code == 403
    assert client.delete(url(org, declaration)).status_code == 403
    declaration.refresh_from_db()
    assert declaration.status == DECLARATION_STATUS_SUBMITTED
    assert declaration.submission == submission
    assert declaration.amount == 1500


@pytest.mark.django_db
def test_draft_locked_while_changed(client, org, infra, supports, monkeypatch):
    """
    PUT and DELETE lock the draft in a transaction, as the submission does,
    so that they don't run at the same time (C5). SQLite ignores the lock:
    only the transaction is checked, within the test's one.
    """
    connection = transaction.get_connection()
    test_depth = len(connection.atomic_blocks)
    locked = []
    select_for_update = QuerySet.select_for_update

    def record(queryset, *args, **kwargs):
        if queryset.model is Declaration:
            locked.append(len(connection.atomic_blocks) > test_depth)
        return select_for_update(queryset, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "select_for_update", record)
    response = client.post(url(org), new_support(infra), format="json")
    declaration = Declaration.objects.get(id=response.json()["id"])
    response = client.put(
        url(org, declaration), new_support(infra, amount=10), format="json"
    )
    assert response.status_code == 200, response.json()
    assert locked == [True]
    assert client.delete(url(org, declaration)).status_code == 204
    assert locked == [True, True]
    assert not Declaration.objects.exists()


@pytest.mark.django_db
def test_declarations_access(client, member, admin_user, org, infra):
    Currency.objects.get_or_create(id="EUR")
    infra_to_check = EntityFactory.create(scope=ENTITY_SCOPE_TO_CHECK)
    response = client.post(url(org), new_support(infra_to_check), format="json")
    assert response.status_code == 201, response.json()
    declaration = Declaration.objects.get()
    # The entities missing from the public site
    entities = client.get(url(org)).json()["entities"]
    assert list(entities) == [str(infra_to_check.id)]

    # The TSOSI team only reads
    staff = APIClient()
    staff.force_login(admin_user)
    assert len(staff.get(url(org)).json()["declarations"]) == 1
    response = staff.post(url(org), new_support(infra), format="json")
    assert response.status_code == 403
    assert staff.delete(url(org, declaration)).status_code == 403

    # Members without the option only edit their profile
    member.memberships.update(can_declare_supports=False)
    response = client.post(url(org), new_support(infra), format="json")
    assert response.status_code == 403
    assert client.delete(url(org, declaration)).status_code == 403

    # Other organizations get a 404, anonymous users a 403
    other = EntityFactory.create()
    assert client.get(url(other)).status_code == 404
    assert APIClient().get(url(org)).status_code == 403
    assert Declaration.objects.count() == 1
