import datetime
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from tsosi.api.hub import base, session
from tsosi.api.hub.entities import (
    SUPPORT_STATUS_CONFIRMED,
    SUPPORT_STATUS_NOT_CONFIRMED,
)
from tsosi.data.ingestion.transfer_matching import merge_transfers
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity, Membership, Transfer
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK
from tsosi.models.membership import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_REVOKED,
)

from .factories import (
    DataLoadSourceFactory,
    EntityFactory,
    IdentifierFactory,
    TransferFactory,
)

LINK_URL = "/api/hub/login-link"
LOGIN_URL = "/api/hub/login"
LOGOUT_URL = "/api/hub/logout"
ME_URL = "/api/hub/me"
MEMBERSHIP_ADMIN_URL = "/admin/tsosi/membership/"


@pytest.fixture(autouse=True)
def setup(settings, monkeypatch):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    # Reset the throttling
    cache.clear()
    monkeypatch.setattr(session, "run_in_background", lambda f, *a: f(*a))


@pytest.fixture
def member(db):
    user = get_user_model().objects.create_user(
        username="member@uni.edu", email="member@uni.edu"
    )
    Membership.objects.create(user=user, entity=EntityFactory.create())
    return user


def login_token(client: APIClient, email: str) -> str:
    """Ask for a login link and return the token of the e-mail sent."""
    mail.outbox.clear()
    assert client.post(LINK_URL, {"email": email}).status_code == 204
    assert len(mail.outbox) == 1
    return re.search(r"/hub/login#token=(\S+)", mail.outbox[0].body)[1]


@pytest.mark.django_db
def test_login(member, registries):
    organization = member.memberships.get().entity
    IdentifierFactory.create(
        entity=organization, registry_id=REGISTRY_TSOSI, value="T123456"
    )
    client = APIClient()
    assert client.get(ME_URL).status_code == 403

    # The e-mail is case insensitive
    token = login_token(client, "Member@Uni.edu")
    assert mail.outbox[0].to == ["member@uni.edu"]

    response = client.post(LOGIN_URL, {"token": token})
    assert response.status_code == 200
    assert response.json() == {
        "email": "member@uni.edu",
        "is_staff": False,
        "organization": {
            "id": str(organization.id),
            # The ID of its Hub's URL
            "tsosi_id": "T123456",
            "name": organization.name,
        },
        "can_declare_supports": True,
    }
    assert client.get(ME_URL).json() == response.json()

    # The token is single-use
    assert APIClient().post(LOGIN_URL, {"token": token}).status_code == 400
    # The session lasts a day
    assert client.cookies["sessionid"]["max-age"] == 24 * 60 * 60

    assert client.post(LOGOUT_URL).status_code == 204
    assert client.get(ME_URL).status_code == 403


@pytest.mark.django_db
def test_login_link_only_for_active_members(member):
    get_user_model().objects.create_user(
        username="nomember@uni.edu", email="nomember@uni.edu"
    )
    client = APIClient()
    for email in ["unknown@uni.edu", "nomember@uni.edu"]:
        response = client.post(LINK_URL, {"email": email})
        # Same response, no e-mail sent
        assert response.status_code == 204
    assert len(mail.outbox) == 0

    member.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    assert client.post(LINK_URL, {"email": member.email}).status_code == 204
    assert len(mail.outbox) == 0

    assert client.post(LINK_URL, {"email": "wrong"}).status_code == 400


def login_link(client: APIClient, data: dict) -> str:
    """Ask for a login link and return it, without throttling."""
    cache.clear()
    mail.outbox.clear()
    assert client.post(LINK_URL, data).status_code == 204
    return re.search(r"https?://\S+/hub/login\S*", mail.outbox[0].body)[0]


@pytest.mark.django_db
def test_login_link_next(member, settings):
    settings.TSOSI_FRONTEND_URL = "https://tsosi.org"
    client = APIClient()
    email = member.email
    # A shared link to the Hub: its query is kept, encoded
    link = login_link(
        client, {"email": email, "next": "/hub/T123456?tab=page&status=x#a"}
    )
    assert re.fullmatch(
        r"https://tsosi\.org/hub/login"
        r"\?next=/hub/T123456%3Ftab%3Dpage%26status%3Dx%23a#token=\S+",
        link,
    )
    link = login_link(client, {"email": email, "next": "/hub?tab=page"})
    assert link.startswith("https://tsosi.org/hub/login?next=/hub%3Ftab")
    # The token is still read from the hash
    assert login_token(client, email)

    # Anything else than a Hub page of the frontend is ignored
    for next_path in [
        "",
        "https://evil.org/hub",
        "//evil.org/hub",
        "/\\evil.org/hub",
        "/hubevil",
        "/hub/../admin",
        "/hub/./x",
        "/hub/login",
        "/hub/login?next=/hub",
        "/explore?x=/hub",
        "hub",
        "/hub/" + "x" * 2000,
    ]:
        link = login_link(client, {"email": email, "next": next_path})
        assert re.fullmatch(r"https://tsosi\.org/hub/login#token=\S+", link)


@pytest.mark.django_db
def test_revoked_member_loses_access(member):
    client = APIClient()
    token = login_token(client, member.email)
    member.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    assert client.post(LOGIN_URL, {"token": token}).status_code == 400

    member.memberships.update(status=MEMBERSHIP_STATUS_ACTIVE)
    token = login_token(client, member.email)
    assert client.post(LOGIN_URL, {"token": token}).status_code == 200
    member.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    assert client.get(ME_URL).status_code == 403


@pytest.mark.django_db
def test_invalid_token(member):
    response = APIClient().post(LOGIN_URL, {"token": "wrong"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_csrf(member):
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(LINK_URL, {"email": member.email})
    assert response.status_code == 403
    # Any Hub request sets the CSRF cookie
    client.get(ME_URL)
    csrf_token = client.cookies["csrftoken"].value
    response = client.post(
        LINK_URL, {"email": member.email}, HTTP_X_CSRFTOKEN=csrf_token
    )
    assert response.status_code == 204


@pytest.mark.django_db
def test_login_link_throttle(member):
    client = APIClient()
    for _ in range(10):
        assert client.post(LINK_URL, {"email": "a@b.org"}).status_code == 204
    assert client.post(LINK_URL, {"email": "a@b.org"}).status_code == 429


@pytest.mark.django_db
def test_add_member(admin_client, admin_user, member):
    entity = EntityFactory.create()
    response = admin_client.post(
        f"{MEMBERSHIP_ADMIN_URL}add/",
        {
            "email": "New@Uni.edu",
            "entity": entity.id,
            "status": MEMBERSHIP_STATUS_ACTIVE,
            # Unchecked: profile only, as for an infrastructure
        },
    )
    assert response.status_code == 302
    membership = Membership.objects.get(entity=entity)
    assert membership.user.email == "new@uni.edu"
    assert membership.added_by == admin_user
    assert not membership.can_declare_supports

    # A user is an active member of one organization only
    response = admin_client.post(
        f"{MEMBERSHIP_ADMIN_URL}add/",
        {
            "email": member.email,
            "entity": entity.id,
            "status": MEMBERSHIP_STATUS_ACTIVE,
        },
    )
    assert response.status_code == 200
    assert "only be an active member" in str(response.context["errors"])
    assert not Membership.objects.filter(user=member, entity=entity).exists()


@pytest.mark.django_db
def test_add_member_invitation(
    admin_client, django_capture_on_commit_callbacks
):
    entity = EntityFactory.create(name="Uni")
    data = {
        "email": "new@uni.edu",
        "entity": entity.id,
        "status": MEMBERSHIP_STATUS_ACTIVE,
        "can_declare_supports": "on",
        "send_invitation": "on",
    }
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            f"{MEMBERSHIP_ADMIN_URL}add/", data, follow=True
        )
    assert response.status_code == 200
    assert "An invitation e-mail was sent to new@uni.edu" in str(
        list(response.context["messages"])
    )
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["new@uni.edu"]
    assert "member of Uni on the TSOSI Data" in message.body
    assert "declare and confirm" in message.body
    assert "/hub/login and enter this e-mail address" in message.body
    # No login token: it would expire
    assert "token" not in message.body

    # Profile only, as for an infrastructure
    other = EntityFactory.create()
    profile_only = {
        k: v for k, v in data.items() if k != "can_declare_supports"
    }
    with django_capture_on_commit_callbacks(execute=True):
        admin_client.post(
            f"{MEMBERSHIP_ADMIN_URL}add/",
            {**profile_only, "email": "infra@org.org", "entity": other.id},
        )
    assert len(mail.outbox) == 2
    assert mail.outbox[1].to == ["infra@org.org"]
    assert "declare" not in mail.outbox[1].body
    assert "edit your organization's public page" in mail.outbox[1].body

    # Unchecked
    data_unchecked = {k: v for k, v in data.items() if k != "send_invitation"}
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            f"{MEMBERSHIP_ADMIN_URL}add/",
            {**data_unchecked, "email": "quiet@uni.edu", "entity": other.id},
        )
    assert response.status_code == 302
    assert Membership.objects.filter(user__email="quiet@uni.edu").exists()
    assert len(mail.outbox) == 2

    # Not for a revoked membership
    with django_capture_on_commit_callbacks(execute=True):
        admin_client.post(
            f"{MEMBERSHIP_ADMIN_URL}add/",
            {
                **data,
                "email": "revoked@uni.edu",
                "status": MEMBERSHIP_STATUS_REVOKED,
            },
        )
    assert Membership.objects.filter(user__email="revoked@uni.edu").exists()
    assert len(mail.outbox) == 2

    # Not when a membership is edited: the option isn't on its form
    membership = Membership.objects.get(user__email="new@uni.edu")
    url = f"{MEMBERSHIP_ADMIN_URL}{membership.pk}/change/"
    response = admin_client.get(url)
    assert "send_invitation" not in response.content.decode()
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(url, profile_only)
    assert response.status_code == 302
    membership.refresh_from_db()
    assert not membership.can_declare_supports
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_me_staff(admin_user):
    client = APIClient()
    client.force_login(admin_user)
    assert client.get(ME_URL).json() == {
        "email": admin_user.email,
        "is_staff": True,
        "organization": None,
        "can_declare_supports": False,
    }


@pytest.mark.django_db
def test_entity_preview(member, admin_user, registries):
    entity = member.memberships.get().entity
    entity.scope = ENTITY_SCOPE_TO_CHECK
    entity.save()
    url = f"/api/hub/entities/{entity.id}"
    client = APIClient()
    client.force_login(member)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["name"] == entity.name
    assert response.json()["preview_reason"] == ENTITY_SCOPE_TO_CHECK

    entity.scope = ENTITY_SCOPE_IN
    entity.save()
    assert client.get(url).json()["preview_reason"] == "no_public_support"
    entity.is_recipient = True
    entity.save()
    assert client.get(url).json()["preview_reason"] is None
    # Also by its TSOSI ID, that of the Hub's URLs
    IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_TSOSI, value="T123456"
    )
    response = client.get("/api/hub/entities/T123456")
    assert response.json()["id"] == str(entity.id)

    # Only for the organization's members and the TSOSI team
    other = EntityFactory.create()
    assert client.get(f"/api/hub/entities/{other.id}").status_code == 404
    assert APIClient().get(url).status_code == 403
    staff_client = APIClient()
    staff_client.force_login(admin_user)
    response = staff_client.get(f"/api/hub/entities/{other.id}")
    assert response.status_code == 200


@pytest.mark.django_db
def test_entity_transfers(member, admin_user, datasources):
    org = member.memberships.get().entity
    infra = EntityFactory.create(scope=ENTITY_SCOPE_IN)
    infra_to_check = EntityFactory.create(scope=ENTITY_SCOPE_TO_CHECK)
    consortium = EntityFactory.create()
    doaj_old, doaj, couperin, own = [
        DataLoadSourceFactory.create(
            data_source_id=source,
            entity=entity,
            date_data_obtained=datetime.date.fromisoformat(date),
        )
        for source, entity, date in [
            ("doaj", infra, "2024-01-01"),
            ("doaj", infra, "2025-02-14"),
            ("couperin", consortium, "2025-06-01"),
            ("rennes", org, "2024-03-01"),
        ]
    ]
    # Declared by the infrastructure in two reports and by the organization
    confirmed = merge_transfers(
        TransferFactory.create(
            emitter=org, recipient=infra, data_load_sources=[doaj_old, doaj]
        ),
        TransferFactory.create(
            emitter=org, recipient=infra, data_load_sources=[own]
        ),
    )
    Transfer.objects.filter(id=confirmed.id).update(hide_amount=True)
    # To an infrastructure not in scope yet, through a consortium
    to_check = TransferFactory.create(
        emitter=org,
        recipient=infra_to_check,
        agents=[consortium],
        data_load_sources=[couperin],
    )
    no_amount = TransferFactory.create(
        emitter=org, recipient=infra, data_load_sources=[doaj]
    )
    Transfer.objects.filter(id=no_amount.id).update(
        amount=None, currency=None, amounts_clc=None
    )
    # Another organization's transfer, and a child's: managed in its own Hub
    TransferFactory.create(recipient=infra, data_load_sources=[doaj])
    child = EntityFactory.create()
    child.parents.add(org)
    TransferFactory.create(
        emitter=child, recipient=infra, data_load_sources=[doaj]
    )

    url = f"/api/hub/entities/{org.id}/transfers"
    client = APIClient()
    client.force_login(member)
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    # The merged transfers only, not their sources
    transfers = {t["id"]: t for t in data["transfers"]}
    assert set(transfers) == {
        str(t.id) for t in [confirmed, to_check, no_amount]
    }

    # Only those to a beneficiary in scope are on the public site
    assert transfers[str(confirmed.id)]["is_public"]
    assert not transfers[str(to_check.id)]["is_public"]

    row = transfers[str(confirmed.id)]
    # Hidden on the public site, shown in the Hub
    assert row["amount"] == Transfer.objects.get(id=confirmed.id).amount
    assert row["amount_hidden"] is True
    assert row["status"] == SUPPORT_STATUS_CONFIRMED
    # One line per organization, with its latest data
    assert row["declared_by"] == [
        {
            "id": str(org.id),
            "name": org.name,
            "short_name": None,
            "date": "2024-03-01",
        },
        {
            "id": str(infra.id),
            "name": infra.name,
            "short_name": None,
            "date": "2025-02-14",
        },
    ]

    row = transfers[str(to_check.id)]
    assert row["status"] == SUPPORT_STATUS_NOT_CONFIRMED
    assert row["agent_ids"] == [str(consortium.id)]
    assert row["amount_hidden"] is False
    assert row["declared_by"] == [
        {
            "id": str(consortium.id),
            "name": consortium.name,
            "short_name": None,
            "date": "2025-06-01",
        }
    ]

    row = transfers[str(no_amount.id)]
    assert row["amount"] is None and row["currency"] is None
    assert row["amount_hidden"] is False

    # The entities missing from the public site: none of them has a public
    # transfer here, as the enrichment didn't run.
    assert set(data["entities"]) == {
        str(e.id) for e in [org, infra, infra_to_check, consortium]
    }
    assert data["entities"][str(infra_to_check.id)] == {
        "id": str(infra_to_check.id),
        "name": infra_to_check.name,
        "short_name": infra_to_check.short_name,
        "country": infra_to_check.country,
        "icon": None,
        "identifiers": [],
        "is_recipient": False,
        "scope": ENTITY_SCOPE_TO_CHECK,
        "is_public": False,
        "is_new": False,
    }
    infra.is_recipient = True
    infra.save()
    assert str(infra.id) not in client.get(url).json()["entities"]
    # Public for another role: its scope is still needed
    infra_to_check.is_agent = True
    infra_to_check.save()
    entities = client.get(url).json()["entities"]
    assert entities[str(infra_to_check.id)]["scope"] == ENTITY_SCOPE_TO_CHECK

    # Only for the organization's members and the TSOSI team
    other = EntityFactory.create()
    response = client.get(f"/api/hub/entities/{other.id}/transfers")
    assert response.status_code == 404
    assert APIClient().get(url).status_code == 403
    staff_client = APIClient()
    staff_client.force_login(admin_user)
    response = staff_client.get(f"/api/hub/entities/{other.id}/transfers")
    assert response.status_code == 200
    assert response.json() == {
        "transfers": [],
        "entities": {
            str(other.id): base.HubEntitySerializer(
                base.with_hub_status(Entity.objects.filter(id=other.id)).get()
            ).data
        },
    }
    assert staff_client.get(url).json() == client.get(url).json()
