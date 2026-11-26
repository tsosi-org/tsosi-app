"""
Several members of one organization in the Hub: the drafts are the
organization's, shared by its members, who change, undo and submit each
other's, at once or one after the other.
"""

import threading

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from rest_framework.test import APIClient

from tsosi.api.hub.declarations import DeclarationSerializer
from tsosi.models import Currency, Declaration, Membership
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_STATUS_DRAFT,
    DECLARATION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN
from tsosi.models.membership import MEMBERSHIP_STATUS_REVOKED

from .factories import DataLoadSourceFactory, EntityFactory, TransferFactory


@pytest.fixture
def org(db):
    Currency.objects.get_or_create(id="EUR")
    return EntityFactory.create()


@pytest.fixture
def infra(db):
    return EntityFactory.create(scope=ENTITY_SCOPE_IN, is_recipient=True)


def member_of(entity, email: str):
    user = get_user_model().objects.create_user(username=email, email=email)
    Membership.objects.create(user=user, entity=entity)
    return user


def client_of(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def alice(org):
    return member_of(org, "alice@uni.edu")


@pytest.fixture
def bob(org):
    return member_of(org, "bob@uni.edu")


def year(value: str) -> dict:
    return {"value": f"{value}-01-01", "precision": "year"}


def support(org, infra, amount=1000):
    """A support of the organization, declared by the infrastructure."""
    return TransferFactory.create(
        emitter=org,
        recipient=infra,
        amount=amount,
        currency_id="EUR",
        date_invoice=None,
        date_payment_emitter=None,
        date_payment_recipient=year("2024"),
        date_start=None,
        date_end=None,
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id="doaj", entity=infra)
        ],
    )


def url(org, declaration_id=None) -> str:
    base = f"/api/hub/entities/{org.id}/declarations"
    return f"{base}/{declaration_id}" if declaration_id else base


def new_support(infra, **values) -> dict:
    return {
        "kind": DECLARATION_KIND_NEW,
        "recipient_id": str(infra.id),
        "amount": 1500,
        "currency": "EUR",
        "date_invoice": "2024-03",
        **values,
    }


def edit(transfer, infra, amount) -> dict:
    return new_support(
        infra,
        kind=DECLARATION_KIND_EDIT,
        transfer_id=str(transfer.id),
        amount=amount,
    )


def drafts(client, org) -> list[dict]:
    return client.get(url(org)).json()["declarations"]


def submit(client, org):
    """Preview the drafts, then submit those previewed."""
    preview = client.get(
        f"/api/hub/entities/{org.id}/publication-preview"
    ).json()
    return client.post(
        f"/api/hub/entities/{org.id}/submissions",
        {
            "consent": True,
            "declaration_ids": preview["declaration_ids"],
            "declarations_hash": preview["declarations_hash"],
        },
        format="json",
    )


@pytest.mark.django_db
def test_members_share_the_drafts(org, infra, alice, bob):
    """
    The drafts are the organization's: each member sees, changes and undoes
    those of the others. The author stays the member who created it, the
    history records who changed it.
    """
    transfer = support(org, infra)
    a, b = client_of(alice), client_of(bob)
    response = a.post(url(org), edit(transfer, infra, 2000), format="json")
    assert response.status_code == 201, response.json()
    draft_id = response.json()["id"]

    [draft] = drafts(b, org)
    assert draft["id"] == draft_id
    assert draft["author"] == alice.email
    response = b.put(
        url(org, draft_id), edit(transfer, infra, 3000), format="json"
    )
    assert response.status_code == 200, response.json()
    [draft] = drafts(a, org)
    assert draft["amount"] == 3000
    # Created by Alice, changed by Bob: only the history tells
    assert draft["author"] == alice.email
    declaration = Declaration.objects.get(id=draft_id)
    assert [
        h.history_user for h in declaration.history.order_by("history_date")
    ] == [
        alice,
        bob,
    ]

    # Undone by Bob while Alice edits it: Alice's save gets a 404, the
    # draft isn't created again
    assert b.delete(url(org, draft_id)).status_code == 204
    response = a.put(
        url(org, draft_id), edit(transfer, infra, 4000), format="json"
    )
    assert response.status_code == 404
    assert not Declaration.objects.exists()


@pytest.mark.django_db
def test_member_submits_the_drafts_of_others(org, infra, alice, bob):
    """
    A submission takes all the organization's drafts, those of the other
    members too: Bob consents to Alice's changes, shown in his preview.
    """
    first, second = support(org, infra), support(org, infra, amount=1200)
    a, b = client_of(alice), client_of(bob)
    a.post(url(org), edit(first, infra, 2000), format="json")
    b.post(
        url(org),
        {"kind": DECLARATION_KIND_CONFIRMATION, "transfer_id": str(second.id)},
        format="json",
    )
    response = submit(b, org)
    assert response.status_code == 201, response.json()
    assert response.json()["submitted_by"] == bob.email
    assert response.json()["changes_count"] == 2
    authors = {d.author.email: d.status for d in Declaration.objects.all()}
    assert authors == {
        alice.email: DECLARATION_STATUS_SUBMITTED,
        bob.email: DECLARATION_STATUS_SUBMITTED,
    }
    # Alice sees it waiting, read-only
    submissions = a.get(f"/api/hub/entities/{org.id}/submissions").json()
    assert [s["submitted_by"] for s in submissions] == [bob.email]
    [draft] = [d for d in drafts(a, org) if d["author"] == alice.email]
    response = a.put(
        url(org, draft["id"]), edit(first, infra, 5000), format="json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_drafts_of_a_revoked_member(org, infra, alice, bob):
    """
    The organization changes its contact: the drafts of the revoked member
    stay, for the other members to change, undo or submit.
    """
    transfer = support(org, infra)
    response = client_of(alice).post(
        url(org), edit(transfer, infra, 2000), format="json"
    )
    draft_id = response.json()["id"]
    alice.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    a, b = client_of(alice), client_of(bob)
    assert a.get(url(org)).status_code == 403

    [draft] = drafts(b, org)
    assert draft["author"] == alice.email
    response = b.put(
        url(org, draft_id), edit(transfer, infra, 2500), format="json"
    )
    assert response.status_code == 200, response.json()
    response = submit(b, org)
    assert response.status_code == 201, response.json()
    declaration = Declaration.objects.get(id=draft_id)
    assert declaration.status == DECLARATION_STATUS_SUBMITTED
    assert declaration.amount == 2500


@pytest.mark.django_db
def test_two_members_add_the_same_new_support(org, infra, alice, bob):
    """
    Two members add the same support without seeing each other's: both are
    saved, then shown as possible duplicates, to reconcile.
    """
    a, b = client_of(alice), client_of(bob)
    first = a.post(url(org), new_support(infra), format="json").json()["id"]
    second = b.post(url(org), new_support(infra), format="json").json()["id"]
    pairs = b.get(url(org)).json()["possible_duplicates"]
    assert pairs == [[f"new-{first}", f"new-{second}"]]
    # The same support: Bob undoes his
    assert b.delete(url(org, second)).status_code == 204
    assert a.get(url(org)).json()["possible_duplicates"] == []


@pytest.mark.django_db
@pytest.mark.xfail(
    strict=True,
    reason="H1: no version check on PUT, a stale save overwrites the other "
    "member's change",
)
def test_stale_edit_doesnt_overwrite_another_members_change(
    org, infra, alice, bob
):
    """
    Alice and Bob open the same draft. Alice saves first; Bob's save, made
    from the values he loaded before, should be refused (409) rather than
    replace Alice's without either of them knowing.
    """
    transfer = support(org, infra)
    a, b = client_of(alice), client_of(bob)
    draft_id = a.post(
        url(org), edit(transfer, infra, 2000), format="json"
    ).json()["id"]
    [loaded_by_bob] = drafts(b, org)

    assert (
        a.put(
            url(org, draft_id), edit(transfer, infra, 2100), format="json"
        ).status_code
        == 200
    )
    response = b.put(
        url(org, draft_id),
        {
            **edit(transfer, infra, 3000),
            # What a version check would compare
            "date_last_updated": loaded_by_bob["date_last_updated"],
        },
        format="json",
    )
    assert response.status_code == 409
    assert Declaration.objects.get(id=draft_id).amount == 2100


# Concurrent requests: PostgreSQL only, SQLite has no row locks nor
# concurrent writers


@pytest.fixture
def postgres_only(db):
    if connection.vendor != "postgresql":
        pytest.skip("Concurrent requests need PostgreSQL")


def post_at_once(org, payloads: list[tuple[object, dict]]) -> list:
    """
    POST the declarations at the same time, one thread per member: each
    request is validated before any of them is saved, as when two members
    click Save at once. The status codes, or the exceptions raised.
    """
    barrier = threading.Barrier(len(payloads), timeout=10)
    validate = DeclarationSerializer.validate

    def validate_then_wait(serializer, attrs):
        attrs = validate(serializer, attrs)
        barrier.wait()
        return attrs

    results = [None] * len(payloads)

    def run(index, user, payload):
        try:
            response = client_of(user).post(url(org), payload, format="json")
            results[index] = response.status_code
        except Exception as error:  # noqa: BLE001 — a 500 of the view
            results[index] = error
            barrier.abort()
        finally:
            connection.close()

    DeclarationSerializer.validate = validate_then_wait
    try:
        threads = [
            threading.Thread(target=run, args=(i, user, payload))
            for i, (user, payload) in enumerate(payloads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
    finally:
        DeclarationSerializer.validate = validate
    return results


@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="H2: the unique constraint catches the race, as an error 500",
)
def test_concurrent_changes_of_the_same_support(
    postgres_only, org, infra, alice, bob
):
    """
    Alice and Bob confirm the same support at the same time: one is saved,
    the other told that it already has a change (400), not an error 500.
    """
    transfer = support(org, infra)
    payload = {
        "kind": DECLARATION_KIND_CONFIRMATION,
        "transfer_id": str(transfer.id),
    }
    results = post_at_once(org, [(alice, payload), (bob, payload)])
    # One pending change per support: the database holds
    assert Declaration.objects.count() == 1
    assert not any(isinstance(r, IntegrityError) for r in results), results
    assert sorted(results) == [201, 400]


@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(
    strict=True,
    reason="H3: no database constraint on merges, both overlapping merges "
    "are saved",
)
def test_concurrent_merges_of_the_same_support(
    postgres_only, org, infra, alice, bob
):
    """
    Alice marks supports 1 and 2 as the same, Bob 2 and 3, at the same time.
    A support is in one merge at most: one of them must be refused, as it
    is when they're saved one after the other.
    """
    first, second, third = [
        support(org, infra, amount=1000 + i * 100) for i in range(3)
    ]

    def merge(transfer, other) -> dict:
        return {
            "kind": DECLARATION_KIND_MERGE,
            "transfer_id": str(transfer.id),
            "other_transfer_ids": [str(other.id)],
        }

    results = post_at_once(
        org, [(alice, merge(first, second)), (bob, merge(third, second))]
    )
    assert sorted(results) == [201, 400], results
    assert Declaration.objects.filter(kind=DECLARATION_KIND_MERGE).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_new_supports(postgres_only, org, infra, alice, bob):
    """
    Alice and Bob add new supports at the same time: both are saved, as
    drafts of the organization. Checks that `post_at_once` runs the
    requests at once without a constraint at stake.
    """
    results = post_at_once(
        org,
        [(alice, new_support(infra)), (bob, new_support(infra, amount=10))],
    )
    assert results == [201, 201]
    assert sorted(
        Declaration.objects.filter(status=DECLARATION_STATUS_DRAFT).values_list(
            "author__email", flat=True
        )
    ) == [alice.email, bob.email]
