import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tsosi.data.ingestion.transfer_matching import merge_transfers
from tsosi.models import Declaration, Membership
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_STATUS_APPROVED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN

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


def year(value: str) -> dict:
    return {"value": f"{value}-01-01", "precision": "year"}


def support(org, infra, amount=1000, date="2024", source="doaj", **values):
    """A support of the organization, received in the given year."""
    return TransferFactory.create(
        emitter=org,
        recipient=infra,
        amount=amount,
        currency_id="EUR",
        date_invoice=None,
        date_payment_emitter=None,
        date_payment_recipient=year(date),
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id=source, entity=infra)
        ],
        **values,
    )


def matches_url(entity) -> str:
    return f"/api/hub/entities/{entity.id}/matches"


@pytest.mark.django_db
def test_matches(client, admin_user, org, infra, datasources):
    same = support(org, infra)
    other_amount = support(org, infra, amount=1200)
    support(org, infra, date="2023")
    support(org, EntityFactory.create(scope=ENTITY_SCOPE_IN))
    # Not the organization's own: its child's
    child = EntityFactory.create()
    child.parents.add(org)
    support(child, infra)

    query = {
        "recipient_id": str(infra.id),
        "amount": 1000,
        "currency": "EUR",
        "date_payment_recipient": "2024-03",
    }
    response = client.get(matches_url(org), query)
    assert response.status_code == 200, response.json()
    # The same amount first
    assert response.json()["matches"] == [
        {"row_id": str(same.id), "amount_differs": False},
        {"row_id": str(other_amount.id), "amount_differs": True},
    ]
    # Without amount, both match
    response = client.get(
        matches_url(org),
        {"recipient_id": str(infra.id), "date_payment_recipient": "2024"},
    )
    assert {m["amount_differs"] for m in response.json()["matches"]} == {False}
    # No date: no match
    response = client.get(matches_url(org), {"recipient_id": str(infra.id)})
    assert response.json()["matches"] == []
    # Invalid values
    response = client.get(
        matches_url(org), {**query, "date_payment_recipient": "2024-13"}
    )
    assert response.status_code == 400

    # The new supports not published yet too, the one edited excepted
    draft = Declaration.objects.create(
        entity=org,
        kind=DECLARATION_KIND_NEW,
        recipient=infra,
        amount=1000,
        currency_id="EUR",
        date_payment_recipient=year("2024"),
    )
    rows = [
        m["row_id"]
        for m in client.get(matches_url(org), query).json()["matches"]
    ]
    assert rows == [str(same.id), f"new-{draft.id}", str(other_amount.id)]
    response = client.get(
        matches_url(org), {**query, "exclude": f"new-{draft.id}"}
    )
    assert len(response.json()["matches"]) == 2
    draft.delete()

    # The TSOSI team reads too, other organizations get a 404
    staff = APIClient()
    staff.force_login(admin_user)
    assert len(staff.get(matches_url(org), query).json()["matches"]) == 2
    other = EntityFactory.create()
    assert client.get(matches_url(other), query).status_code == 404


def duplicates(client, org) -> set[frozenset]:
    url = f"/api/hub/entities/{org.id}/declarations"
    return {frozenset(p) for p in client.get(url).json()["possible_duplicates"]}


def pair(*rows) -> frozenset:
    return frozenset(str(r.id) if hasattr(r, "pk") else r for r in rows)


@pytest.mark.django_db
def test_possible_duplicates(client, org, infra, datasources):
    first = support(org, infra)
    second = support(org, infra, amount=1100, source="couperin")
    support(org, infra, date="2023")
    assert duplicates(client, org) == {pair(first, second)}

    # Declared different supports, in an approved declaration
    declaration = Declaration.objects.create(
        entity=org,
        kind=DECLARATION_KIND_NOT_DUPLICATE,
        transfer=first,
        status=DECLARATION_STATUS_APPROVED,
    )
    declaration.other_transfers.set([second])
    assert duplicates(client, org) == set()
    # Even once merged with another source
    third = support(org, infra, source="pkp")
    merged = merge_transfers(first, third)
    assert duplicates(client, org) == set()

    # A new support declared with the matches it isn't
    declaration.delete()
    assert duplicates(client, org) == {pair(merged, second)}
    new = Declaration.objects.create(
        entity=org,
        kind=DECLARATION_KIND_NEW,
        status=DECLARATION_STATUS_APPROVED,
        published_transfer=second,
    )
    new.other_transfers.set([first])
    assert duplicates(client, org) == set()


@pytest.mark.django_db
def test_possible_duplicates_of_drafts(client, org, infra, datasources):
    """All the saved rows are compared, with their declared values."""
    published = support(org, infra)
    other = support(org, infra, date="2023")
    values = {
        "recipient": infra,
        "amount": 1000,
        "currency_id": "EUR",
        "date_payment_recipient": year("2024"),
    }
    first_new = Declaration.objects.create(
        entity=org, kind=DECLARATION_KIND_NEW, **values
    )
    second_new = Declaration.objects.create(
        entity=org, kind=DECLARATION_KIND_NEW, **values
    )
    first_key, second_key = f"new-{first_new.id}", f"new-{second_new.id}"
    assert duplicates(client, org) == {
        pair(published, first_key),
        pair(published, second_key),
        pair(first_key, second_key),
    }
    # An edit is compared with its values
    edit = Declaration.objects.create(
        entity=org, kind=DECLARATION_KIND_EDIT, transfer=other, **values
    )
    assert len(duplicates(client, org)) == 6
    edit.delete()

    # A new support that isn't the published one, nor the other new one
    response = client.put(
        declarations_url(org, first_new),
        {
            "kind": DECLARATION_KIND_NEW,
            "recipient_id": str(infra.id),
            "amount": 1000,
            "currency": "EUR",
            "date_payment_recipient": "2024",
            "other_transfer_ids": [str(published.id)],
            "other_declaration_ids": [second_new.id],
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["other_declaration_ids"] == [second_new.id]
    assert duplicates(client, org) == {pair(published, second_key)}
    # Only other new supports
    response = client.put(
        declarations_url(org, second_new),
        {
            "kind": DECLARATION_KIND_NEW,
            "recipient_id": str(infra.id),
            "amount": 1000,
            "currency": "EUR",
            "date_payment_recipient": "2024",
            "other_declaration_ids": [second_new.id],
        },
        format="json",
    )
    assert "other_declaration_ids" in response.json()


def declarations_url(entity, declaration=None) -> str:
    base = f"/api/hub/entities/{entity.id}/declarations"
    return f"{base}/{declaration.id}" if declaration else base


def reconcile(client, org, kind, transfer, *others):
    return client.post(
        declarations_url(org),
        {
            "kind": kind,
            "transfer_id": str(transfer.id),
            "other_transfer_ids": [str(o.id) for o in others],
        },
        format="json",
    )


@pytest.mark.django_db
def test_merge_and_not_duplicate(client, org, infra, datasources):
    first, second, third = [
        support(org, infra, amount=1000 + i * 100) for i in range(3)
    ]
    not_own = support(EntityFactory.create(), infra)
    for kind in [DECLARATION_KIND_MERGE, DECLARATION_KIND_NOT_DUPLICATE]:
        # The other support is required, and can't be the same
        response = reconcile(client, org, kind, first)
        assert "other_transfer_ids" in response.json()
        response = reconcile(client, org, kind, first, first)
        assert "itself" in str(response.json())
        # Only the organization's own supports
        response = reconcile(client, org, kind, first, not_own)
        assert "own supports" in str(response.json())

    response = reconcile(client, org, DECLARATION_KIND_MERGE, first, second)
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["other_transfer_ids"] == [str(second.id)]
    # Only the transfers' values are published
    assert data["amount"] is None and data["recipient_id"] is None
    # A support is in one merge at most
    response = reconcile(client, org, DECLARATION_KIND_MERGE, third, second)
    assert "already marked as the same" in str(response.json())
    # Not both the same and different
    response = reconcile(
        client, org, DECLARATION_KIND_NOT_DUPLICATE, second, first
    )
    assert "marked as the same support" in str(response.json())
    # But different from another one, with other changes
    response = reconcile(
        client, org, DECLARATION_KIND_NOT_DUPLICATE, first, third
    )
    assert response.status_code == 201, response.json()

    # One change for the merged supports
    response = client.post(
        declarations_url(org),
        {"kind": DECLARATION_KIND_CONFIRMATION, "transfer_id": str(first.id)},
        format="json",
    )
    assert response.status_code == 201, response.json()
    response = client.post(
        declarations_url(org),
        {"kind": DECLARATION_KIND_CONFIRMATION, "transfer_id": str(second.id)},
        format="json",
    )
    assert "marked as the same as another one" in str(response.json())
    # And none to merge two changed supports
    Declaration.objects.filter(kind=DECLARATION_KIND_MERGE).delete()
    client.post(
        declarations_url(org),
        {"kind": DECLARATION_KIND_CONFIRMATION, "transfer_id": str(second.id)},
        format="json",
    )
    response = reconcile(client, org, DECLARATION_KIND_MERGE, first, second)
    assert "Several of these supports" in str(response.json())


@pytest.mark.django_db
def test_new_support_matched(client, org, infra, datasources):
    """A new support becomes the confirmation or edit of its match."""
    matched = support(org, infra)
    other = support(org, infra, amount=1200)
    response = client.post(
        declarations_url(org),
        {
            "kind": DECLARATION_KIND_NEW,
            "recipient_id": str(infra.id),
            "amount": 1000,
            "currency": "EUR",
            "date_payment_recipient": "2024",
            # The member chose "none of these"
            "other_transfer_ids": [str(matched.id), str(other.id)],
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert set(response.json()["other_transfer_ids"]) == {
        str(matched.id),
        str(other.id),
    }
    declaration = Declaration.objects.get()

    # It's the first one after all
    response = client.put(
        declarations_url(org, declaration),
        {
            "kind": DECLARATION_KIND_EDIT,
            "transfer_id": str(matched.id),
            "recipient_id": str(infra.id),
            "amount": 1050,
            "currency": "EUR",
            "date_payment_recipient": "2024",
            "other_transfer_ids": [str(other.id)],
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["kind"] == DECLARATION_KIND_EDIT
    assert data["transfer_id"] == str(matched.id)
    # Only reconciliations have other transfers
    assert data["other_transfer_ids"] == []
    # It's a change of that support now: its transfer doesn't change
    response = client.put(
        declarations_url(org, declaration),
        {"kind": DECLARATION_KIND_CONFIRMATION, "transfer_id": str(other.id)},
        format="json",
    )
    assert "can't be changed" in str(response.json())
    response = client.put(
        declarations_url(org, declaration),
        {"kind": DECLARATION_KIND_REMOVAL, "transfer_id": str(matched.id)},
        format="json",
    )
    assert "Only the supports that the organization declared" in str(
        response.json()
    )
