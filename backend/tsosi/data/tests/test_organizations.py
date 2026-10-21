import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tsosi.data.pid_registry.lookup import (
    REGISTRY_ROR,
    REGISTRY_WIKIDATA,
    OrganizationRecord,
    RegistryError,
    fetch_organization_record,
    parse_organization_id,
)
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import (
    Currency,
    Entity,
    EntityName,
    IdentifierEntityMatching,
    Membership,
)
from tsosi.models.declaration import DECLARATION_KIND_NEW
from tsosi.models.entity import (
    ENTITY_SCOPE_IN,
    ENTITY_SCOPE_OUT,
    ENTITY_SCOPE_TO_CHECK,
)

from .factories import EntityFactory, IdentifierFactory, TransferFactory
from .utils import MockAiohttpResponse

SEARCH_URL = "/api/hub/organizations"


@pytest.fixture(autouse=True)
def local_cache(settings):
    """A cache of its own, without the registry records of other tests."""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }


def create_member(entity, email: str):
    user = get_user_model().objects.create_user(username=email, email=email)
    Membership.objects.create(user=user, entity=entity)
    return user


@pytest.fixture
def org(db):
    return EntityFactory.create()


@pytest.fixture
def member(org):
    return create_member(org, "member@uni.edu")


@pytest.fixture
def client(member) -> APIClient:
    client = APIClient()
    client.force_login(member)
    return client


@pytest.fixture
def record_fetch(mocker):
    """The registry lookups, mocked: the record of 05abcde12."""

    def fetch(registry, value):
        if value != "05abcde12":
            return None
        return OrganizationRecord(
            registry=registry,
            id=value,
            name="Open Infrastructure",
            country="FR",
            website="https://infra.org",
            other_ids={REGISTRY_WIKIDATA: "Q123"},
            record={"id": value},
        )

    return mocker.patch(
        "tsosi.api.hub.organizations.fetch_organization_record",
        side_effect=fetch,
    )


def add_url(entity) -> str:
    return f"/api/hub/entities/{entity.id}/organizations"


def search(client, query) -> dict:
    response = client.get(SEARCH_URL, {"search": query})
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.mark.parametrize(
    "value, expected",
    [
        ("02rx3b187", (REGISTRY_ROR, "02rx3b187")),
        (" https://ror.org/02RX3B187 ", (REGISTRY_ROR, "02rx3b187")),
        ("ror.org/02rx3b187", (REGISTRY_ROR, "02rx3b187")),
        # Copied from the browser's address bar
        ("https://ror.org/02rx3b187/", (REGISTRY_ROR, "02rx3b187")),
        ("https://www.wikidata.org/wiki/Q42/", (REGISTRY_WIKIDATA, "Q42")),
        ("Q42", (REGISTRY_WIKIDATA, "Q42")),
        ("q42", (REGISTRY_WIKIDATA, "Q42")),
        ("https://www.wikidata.org/wiki/Q42", (REGISTRY_WIKIDATA, "Q42")),
        ("http://www.wikidata.org/entity/Q42", (REGISTRY_WIKIDATA, "Q42")),
        ("02rx3b18", None),
        ("https://example.org/02rx3b187", None),
        ("Open Infrastructure", None),
    ],
)
def test_parse_organization_id(value, expected):
    assert parse_organization_id(value) == expected


def test_fetch_ror_organization(mocker, uga_ror_record):
    mocker.patch(
        "aiohttp.ClientSession.get",
        return_value=MockAiohttpResponse(json=uga_ror_record),
    )
    record = fetch_organization_record(REGISTRY_ROR, "02rx3b187")
    assert record.name == "Université Grenoble Alpes"
    assert record.country == "FR"
    assert record.other_ids == {REGISTRY_WIKIDATA: "Q945876"}
    assert record.record == uga_ror_record

    mocker.patch(
        "aiohttp.ClientSession.get",
        return_value=MockAiohttpResponse(status=404),
    )
    assert fetch_organization_record(REGISTRY_ROR, "02rx3b187") is None
    mocker.patch(
        "aiohttp.ClientSession.get",
        return_value=MockAiohttpResponse(status=500),
    )
    with pytest.raises(RegistryError):
        fetch_organization_record(REGISTRY_ROR, "02rx3b187")


@pytest.mark.django_db
def test_search(client, org, registries):
    in_scope = EntityFactory.create(
        name="Directory of Open Access Journals",
        short_name="DOAJ",
        scope=ENTITY_SCOPE_IN,
        is_recipient=True,
    )
    # Not on the public site
    to_check = EntityFactory.create(
        name="Open Journal Index", scope=ENTITY_SCOPE_TO_CHECK
    )
    IdentifierFactory.create(
        entity=to_check, registry_id=REGISTRY_ROR, value="05abcde12"
    )
    supporter = EntityFactory.create(name="University of Open Journals")
    EntityName.objects.create(
        entity=supporter, type="alias", value="UOJ", registry_id=REGISTRY_ROR
    )
    merged = EntityFactory.create(name="Open Journal Old", is_active=False)

    def ids(query):
        return [r["id"] for r in search(client, query)["results"]]

    # Every word, in any name
    assert set(ids("open journal")) == {
        str(e.id) for e in [in_scope, to_check, supporter]
    }
    assert str(merged.id) not in ids("journal")
    # Exact matches first, then those starting with the query
    assert ids("doaj") == [str(in_scope.id)]
    assert ids("open journal")[0] == str(to_check.id)
    assert ids("uoj") == [str(supporter.id)]
    # By identifier, or its URL: found in TSOSI, so not looked up
    assert ids("05abcde12") == [str(to_check.id)]
    data = search(client, "https://ror.org/05abcde12")
    assert [r["id"] for r in data["results"]] == [str(to_check.id)]
    assert data["lookup"] is None
    assert search(client, "") == {"results": [], "lookup": None}

    result = search(client, "index")["results"][0]
    assert result["scope"] == ENTITY_SCOPE_TO_CHECK
    assert result["is_public"] is False
    assert result["is_new"] is False
    assert result["identifiers"] == [
        {"registry": REGISTRY_ROR, "value": "05abcde12"}
    ]

    # For the members and the TSOSI team
    assert APIClient().get(SEARCH_URL, {"search": "doaj"}).status_code == 403


@pytest.mark.django_db
def test_search_lookup(client, registries, record_fetch):
    # Missing from TSOSI: its record, to add it
    data = search(client, "https://ror.org/05abcde12")
    assert data["results"] == []
    assert data["lookup"] == {
        "registry": REGISTRY_ROR,
        "identifier": "05abcde12",
        "record": {
            "registry": REGISTRY_ROR,
            "identifier": "05abcde12",
            "name": "Open Infrastructure",
            "country": "FR",
            "website": "https://infra.org",
        },
        "error": None,
    }
    # Cached: the registry isn't requested again
    search(client, "05abcde12")
    assert record_fetch.call_count == 1

    data = search(client, "05abcde13")
    assert data["lookup"]["record"] is None
    assert data["lookup"]["error"] == "No ROR record has this ID."

    # In TSOSI with the other ID of its record
    infra = EntityFactory.create(scope=ENTITY_SCOPE_OUT)
    IdentifierFactory.create(
        entity=infra, registry_id=REGISTRY_WIKIDATA, value="Q123"
    )
    data = search(client, "05abcde12")
    assert [r["id"] for r in data["results"]] == [str(infra.id)]
    assert data["results"][0]["scope"] == ENTITY_SCOPE_OUT
    assert data["lookup"] is None

    # The registry is down
    record_fetch.side_effect = RegistryError()
    data = search(client, "Q8")
    assert data["lookup"]["error"] == (
        "Wikidata couldn't be reached. Please try again later."
    )


@pytest.mark.django_db
def test_add_organization(
    client, member, org, registries, datasources, record_fetch, mocker
):
    signal = mocker.patch("tsosi.data.entity_edit.identifiers_created.send")
    # From its name only
    response = client.post(add_url(org), {"name": " New Infra "})
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["name"] == "New Infra"
    assert data["is_new"] is True
    assert data["is_public"] is False
    entity = Entity.objects.get(id=data["id"])
    assert list(entity.added_in_hub_by.all()) == [org]
    assert entity.raw_name == "New Infra"
    assert [i.registry_id for i in entity.identifiers.all()] == [REGISTRY_TSOSI]
    assert entity.history.get().history_user == member
    signal.assert_not_called()
    # Not public until a support to it is published
    assert client.get(f"/api/entities/{entity.id}").status_code == 404
    assert str(entity.id) not in {
        e["id"] for e in client.get("/api/entities/all").json()
    }

    # From its ID: its record's name and country, and its record fetched
    response = client.post(
        add_url(org), {"identifier": "https://ror.org/05abcde12"}
    )
    assert response.status_code == 201, response.json()
    entity = Entity.objects.get(id=response.json()["id"])
    assert (entity.name, entity.country) == ("Open Infrastructure", "FR")
    assert entity.website == "https://infra.org"
    ror_id = entity.identifiers.get(registry_id=REGISTRY_ROR)
    assert ror_id.value == "05abcde12"
    matching = IdentifierEntityMatching.objects.get(identifier=ror_id)
    assert matching.comments == "Added in the Hub by member@uni.edu."
    signal.assert_called_once_with(None, registries=[REGISTRY_ROR])

    # Already in TSOSI: that one. Another institution adds it too while no
    # support to it is published.
    other_org = EntityFactory.create()
    other_client = APIClient()
    other_client.force_login(create_member(other_org, "other@uni.edu"))
    response = other_client.post(
        add_url(other_org), {"identifier": "05abcde12"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(entity.id)
    assert set(entity.added_in_hub_by.all()) == {org, other_org}
    # Visible in the other institutions' search
    data = search(other_client, "new infra")
    assert data["results"][0]["is_new"] is True

    TransferFactory.create(emitter=org, recipient=entity)
    third_org = EntityFactory.create()
    third_client = APIClient()
    third_client.force_login(create_member(third_org, "third@uni.edu"))
    response = third_client.post(
        add_url(third_org), {"identifier": "05abcde12"}
    )
    assert response.status_code == 200
    assert response.json()["is_new"] is False
    assert third_org not in entity.added_in_hub_by.all()

    for values, field in [
        ({"identifier": "Open"}, "identifier"),
        ({"identifier": "05abcde13"}, "identifier"),
        ({"name": " "}, "name"),
        ({}, "name"),
    ]:
        response = client.post(add_url(org), values)
        assert response.status_code == 400
        assert field in response.json()

    # Only for the members who can declare supports
    staff = APIClient()
    staff.force_login(
        get_user_model().objects.create_user(username="staff", is_staff=True)
    )
    assert staff.post(add_url(org), {"name": "X"}).status_code == 403
    member.memberships.update(can_declare_supports=False)
    assert client.post(add_url(org), {"name": "X"}).status_code == 403
    assert Entity.objects.filter(name="X").count() == 0


@pytest.mark.django_db
def test_support_to_added_organization(client, org, registries):
    Currency.objects.get_or_create(id="EUR")
    response = client.post(add_url(org), {"name": "New Infra"})
    entity_id = response.json()["id"]
    url = f"/api/hub/entities/{org.id}/declarations"
    response = client.post(
        url,
        {
            "kind": DECLARATION_KIND_NEW,
            "recipient_id": entity_id,
            "amount": 1500,
            "currency": "EUR",
            "date_invoice": "2024",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    # Missing from the reference data: sent with the declarations
    entity = client.get(url).json()["entities"][entity_id]
    assert entity["is_new"] is True
    assert entity["is_public"] is False
    assert entity["scope"] is None
