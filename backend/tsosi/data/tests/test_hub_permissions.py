"""
Access to every endpoint of the Data Contribution Hub, and to the profile
edit of the public API, for each kind of user: one matrix, so that a new
endpoint without its check fails here.
"""

from dataclasses import dataclass

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import URLPattern
from rest_framework.test import APIClient

from tsosi import urls as tsosi_urls
from tsosi.data.hub_publication import drafts_hash, load_declarations
from tsosi.models import Currency, Declaration, Membership, Transfer
from tsosi.models.declaration import (
    DECLARATION_KIND_NEW,
    DECLARATION_STATUS_SUBMITTED,
)
from tsosi.models.entity import ENTITY_SCOPE_IN
from tsosi.models.membership import MEMBERSHIP_STATUS_REVOKED

from .factories import DataLoadSourceFactory, EntityFactory, TransferFactory

ANONYMOUS = "anonymous"
MEMBER = "member"
# A member of the organization without "Can declare supports"
MEMBER_PROFILE_ONLY = "member_profile_only"
OTHER_MEMBER = "other_member"
REVOKED_MEMBER = "revoked_member"
# Logged in, without membership
NO_MEMBERSHIP = "no_membership"
STAFF = "staff"
USERS = [
    ANONYMOUS,
    MEMBER,
    MEMBER_PROFILE_ONLY,
    OTHER_MEMBER,
    REVOKED_MEMBER,
    NO_MEMBERSHIP,
    STAFF,
]


@dataclass
class Hub:
    org: object
    other_org: object
    infra: object
    transfer: Transfer
    draft: Declaration
    users: dict


@pytest.fixture(autouse=True)
def setup(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    cache.clear()


def create_user(email: str, **kwargs):
    return get_user_model().objects.create_user(
        username=email, email=email, **kwargs
    )


@pytest.fixture
def hub(db, datasources, registries) -> Hub:
    Currency.objects.get_or_create(id="EUR")
    org, other_org = EntityFactory.create(), EntityFactory.create()
    infra = EntityFactory.create(scope=ENTITY_SCOPE_IN, is_recipient=True)
    transfer = TransferFactory.create(
        emitter=org,
        recipient=infra,
        currency_id="EUR",
        data_load_sources=[
            DataLoadSourceFactory.create(data_source_id="doaj", entity=infra)
        ],
    )
    users = {
        MEMBER: create_user("member@org.edu"),
        MEMBER_PROFILE_ONLY: create_user("profile@org.edu"),
        OTHER_MEMBER: create_user("member@other.edu"),
        REVOKED_MEMBER: create_user("revoked@org.edu"),
        NO_MEMBERSHIP: create_user("nobody@org.edu"),
        STAFF: create_user("staff@tsosi.org", is_staff=True),
    }
    Membership.objects.create(user=users[MEMBER], entity=org)
    Membership.objects.create(
        user=users[MEMBER_PROFILE_ONLY], entity=org, can_declare_supports=False
    )
    Membership.objects.create(user=users[OTHER_MEMBER], entity=other_org)
    Membership.objects.create(
        user=users[REVOKED_MEMBER],
        entity=org,
        status=MEMBERSHIP_STATUS_REVOKED,
    )
    draft = Declaration.objects.create(
        entity=org,
        author=users[MEMBER],
        kind=DECLARATION_KIND_NEW,
        recipient=infra,
        amount=100,
        currency_id="EUR",
        date_invoice={"value": "2024-01-01", "precision": "year"},
    )
    return Hub(org, other_org, infra, transfer, draft, users)


def client_for(hub: Hub, user: str, **kwargs) -> APIClient:
    client = APIClient(**kwargs)
    if user != ANONYMOUS:
        client.force_login(hub.users[user])
    return client


def new_support(hub: Hub) -> dict:
    return {
        "kind": DECLARATION_KIND_NEW,
        "recipient_id": str(hub.infra.id),
        "amount": 1500,
        "currency": "EUR",
        "date_invoice": "2024-03",
    }


# Each endpoint: (method, URL, body), from the fixture
ENDPOINTS = {
    "me": lambda h: ("get", "/api/hub/me", None),
    "organizations": lambda h: (
        "get",
        "/api/hub/organizations?search=a",
        None,
    ),
    "preview": lambda h: ("get", f"/api/hub/entities/{h.org.id}", None),
    "transfers": lambda h: (
        "get",
        f"/api/hub/entities/{h.org.id}/transfers",
        None,
    ),
    "declarations_list": lambda h: (
        "get",
        f"/api/hub/entities/{h.org.id}/declarations",
        None,
    ),
    "declarations_create": lambda h: (
        "post",
        f"/api/hub/entities/{h.org.id}/declarations",
        new_support(h),
    ),
    "declaration_update": lambda h: (
        "put",
        f"/api/hub/entities/{h.org.id}/declarations/{h.draft.id}",
        {**new_support(h), "amount": 2000},
    ),
    "declaration_delete": lambda h: (
        "delete",
        f"/api/hub/entities/{h.org.id}/declarations/{h.draft.id}",
        None,
    ),
    "organizations_create": lambda h: (
        "post",
        f"/api/hub/entities/{h.org.id}/organizations",
        {"name": "A new beneficiary"},
    ),
    "submissions_list": lambda h: (
        "get",
        f"/api/hub/entities/{h.org.id}/submissions",
        None,
    ),
    "submissions_create": lambda h: (
        "post",
        f"/api/hub/entities/{h.org.id}/submissions",
        {
            "consent": True,
            "declaration_ids": [h.draft.id],
            "declarations_hash": drafts_hash(
                load_declarations(Declaration.objects.filter(id=h.draft.id))
            ),
        },
    ),
    "publication_preview": lambda h: (
        "get",
        f"/api/hub/entities/{h.org.id}/publication-preview",
        None,
    ),
    "profile_edit": lambda h: (
        "patch",
        f"/api/entities/{h.org.id}/edit/",
        {"short_name": "ORG"},
    ),
}

# Reads of the organization's Hub: its members and the TSOSI team. Other
# organizations get a 404, so that they don't learn which IDs exist.
READ = {
    ANONYMOUS: 403,
    MEMBER: 200,
    MEMBER_PROFILE_ONLY: 200,
    OTHER_MEMBER: 404,
    REVOKED_MEMBER: 403,
    NO_MEMBERSHIP: 403,
    STAFF: 200,
}


def write(success: int) -> dict:
    """
    Changes of the organization's supports: its members with the option
    only, the TSOSI team reads them.
    """
    return {**READ, MEMBER: success, MEMBER_PROFILE_ONLY: 403, STAFF: 403}


EXPECTED = {
    "me": {**READ, OTHER_MEMBER: 200},
    "organizations": {**READ, OTHER_MEMBER: 200},
    "preview": READ,
    "transfers": READ,
    "declarations_list": READ,
    "declarations_create": write(201),
    "declaration_update": write(200),
    "declaration_delete": write(204),
    "organizations_create": write(201),
    "submissions_list": READ,
    "submissions_create": write(201),
    "publication_preview": READ,
    # Every member edits the profile, and the TSOSI team. A 403, not a 404,
    # as the public page exists.
    "profile_edit": {**READ, OTHER_MEMBER: 403},
}

# The Hub endpoints for anonymous users: the login
PUBLIC_ROUTES = {"api/hub/login-link", "api/hub/login", "api/hub/logout"}
# The endpoints of `ENDPOINTS` by route, to check that none is missing
ROUTES = {
    "api/hub/me": ["me"],
    "api/hub/organizations": ["organizations"],
    "api/hub/entities/<str:entity_id>": ["preview"],
    "api/hub/entities/<str:entity_id>/transfers": ["transfers"],
    "api/hub/entities/<str:entity_id>/declarations": [
        "declarations_list",
        "declarations_create",
    ],
    "api/hub/entities/<str:entity_id>/declarations/<int:declaration_id>": [
        "declaration_update",
        "declaration_delete",
    ],
    "api/hub/entities/<str:entity_id>/organizations": ["organizations_create"],
    "api/hub/entities/<str:entity_id>/submissions": [
        "submissions_list",
        "submissions_create",
    ],
    "api/hub/entities/<str:entity_id>/publication-preview": [
        "publication_preview"
    ],
}


def request(client: APIClient, method: str, url: str, body, **kwargs):
    return getattr(client, method)(url, body, format="json", **kwargs)


def test_every_hub_route_is_checked():
    routes = {
        str(p.pattern)
        for p in tsosi_urls.urlpatterns
        if isinstance(p, URLPattern) and str(p.pattern).startswith("api/hub/")
    }
    assert routes == set(ROUTES) | PUBLIC_ROUTES
    assert sorted(e for names in ROUTES.values() for e in names) == sorted(
        e for e in ENDPOINTS if e != "profile_edit"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("user", USERS)
@pytest.mark.parametrize("endpoint", list(ENDPOINTS))
def test_access(hub, endpoint, user):
    method, url, body = ENDPOINTS[endpoint](hub)
    response = request(client_for(hub, user), method, url, body)
    assert response.status_code == EXPECTED[endpoint][user], response.content[
        :300
    ]
    if response.status_code >= 400:
        # Nothing changed
        assert Declaration.objects.count() == 1
        hub.draft.refresh_from_db()
        assert hub.draft.amount == 100
        assert hub.draft.status != DECLARATION_STATUS_SUBMITTED


WRITE_ENDPOINTS = [
    "declarations_create",
    "declaration_update",
    "declaration_delete",
    "organizations_create",
    "submissions_create",
    "profile_edit",
]


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS)
def test_csrf(hub, endpoint):
    """Every write needs the CSRF token, the session alone isn't enough."""
    method, url, body = ENDPOINTS[endpoint](hub)
    client = client_for(hub, MEMBER, enforce_csrf_checks=True)
    response = request(client, method, url, body)
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    assert Declaration.objects.count() == 1
    hub.draft.refresh_from_db()
    assert hub.draft.amount == 100

    # Any Hub request sets the CSRF cookie
    client.get("/api/hub/me")
    token = client.cookies["csrftoken"].value
    response = request(client, method, url, body, HTTP_X_CSRFTOKEN=token)
    assert response.status_code < 300, response.content[:300]


@pytest.mark.django_db
@pytest.mark.parametrize("url", sorted(PUBLIC_ROUTES))
def test_csrf_anonymous(hub, url):
    """The login requests too, against login CSRF."""
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(f"/{url}", {}, format="json")
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.fixture
def other_hub(hub):
    """A support and drafts of the other organization."""
    transfer = TransferFactory.create(
        emitter=hub.other_org,
        recipient=hub.infra,
        currency_id="EUR",
        data_load_sources=[
            DataLoadSourceFactory.create(
                data_source_id="doaj", entity=hub.infra
            )
        ],
    )
    draft = Declaration.objects.create(
        entity=hub.other_org,
        author=hub.users[OTHER_MEMBER],
        kind=DECLARATION_KIND_NEW,
        recipient=hub.infra,
        amount=100,
        currency_id="EUR",
        date_invoice={"value": "2024-01-01", "precision": "year"},
    )
    return transfer, draft


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        lambda h, t, d: {"kind": "confirmation", "transfer_id": str(t.id)},
        lambda h, t, d: {
            "kind": "merge",
            "transfer_id": str(h.transfer.id),
            "other_transfer_ids": [str(t.id)],
        },
        lambda h, t, d: {
            "kind": "not_duplicate",
            "transfer_id": str(h.transfer.id),
            "other_transfer_ids": [str(t.id)],
        },
        lambda h, t, d: {**new_support(h), "other_transfer_ids": [str(t.id)]},
        lambda h, t, d: {**new_support(h), "other_declaration_ids": [d.id]},
    ],
    ids=["transfer", "merge", "not_duplicate", "new_match", "new_other"],
)
def test_other_organization_ids_in_payload(hub, other_hub, payload):
    """
    The supports and declarations of another organization can't be
    referred to.
    """
    transfer, draft = other_hub
    client = client_for(hub, MEMBER)
    url = f"/api/hub/entities/{hub.org.id}/declarations"
    response = client.post(url, payload(hub, transfer, draft), format="json")
    assert response.status_code == 400, response.content[:300]
    assert Declaration.objects.filter(entity=hub.org).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["put", "delete"])
def test_other_organization_declaration_in_url(hub, other_hub, method):
    """Another organization's declaration through the member's own Hub."""
    _, draft = other_hub
    client = client_for(hub, MEMBER)
    url = f"/api/hub/entities/{hub.org.id}/declarations/{draft.id}"
    response = request(client, method, url, new_support(hub))
    assert response.status_code == 404
    draft.refresh_from_db()
    assert draft.amount == 100


@pytest.mark.django_db
def test_other_organization_data_not_listed(hub, other_hub):
    """The member's Hub lists nothing of the other organization."""
    transfer, draft = other_hub
    client = client_for(hub, MEMBER)
    base = f"/api/hub/entities/{hub.org.id}"
    transfers = client.get(f"{base}/transfers").json()["transfers"]
    assert [t["id"] for t in transfers] == [str(hub.transfer.id)]
    declarations = client.get(f"{base}/declarations").json()["declarations"]
    assert [d["id"] for d in declarations] == [hub.draft.id]
    # Nor among its possible duplicates
    pairs = client.get(f"{base}/declarations").json()["possible_duplicates"]
    rows = {row for pair in pairs for row in pair}
    assert str(transfer.id) not in rows and f"new-{draft.id}" not in rows
