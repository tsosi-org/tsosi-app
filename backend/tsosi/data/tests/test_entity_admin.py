"""The organizations added by the TSOSI team in the Django admin."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client

from tsosi.data.pid_registry.lookup import (
    REGISTRY_ROR,
    REGISTRY_WIKIDATA,
    OrganizationRecord,
    RegistryError,
)
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity, EntityName, IdentifierEntityMatching
from tsosi.models.entity import ENTITY_SCOPE_IN

from .factories import EntityFactory, IdentifierFactory

ADD_URL = "/admin/tsosi/entity/add/"


@pytest.fixture(autouse=True)
def local_cache(settings):
    """
    A cache of its own, emptied after each test: the registry records are
    cached.
    """
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test_entity_admin",
        }
    }
    yield
    cache.clear()


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        username="admin", email="admin@tsosi.org", password="x"
    )


@pytest.fixture
def client(admin_user) -> Client:
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def signal(mocker):
    return mocker.patch("tsosi.data.entity_edit.identifiers_created.send")


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


def form_errors(response) -> dict:
    form = response.context["form"]
    return {k: [str(e) for e in v] for k, v in form.errors.items()}


def test_add_page(client):
    response = client.get(ADD_URL)
    assert response.status_code == 200
    assert b"Add organization" in response.content
    # The changelist shows the Add button
    response = client.get("/admin/tsosi/entity/")
    assert ADD_URL.encode() in response.content


def test_add_permission(db, registries):
    staff = get_user_model().objects.create_user(
        username="staff", email="staff@tsosi.org", is_staff=True
    )
    client = Client()
    client.force_login(staff)
    assert client.get(ADD_URL).status_code == 403
    assert client.post(ADD_URL, {"name": "Infra"}).status_code == 403
    assert not Entity.objects.exists()


def test_add_from_name(client, admin_user, registries, signal):
    response = client.post(ADD_URL, {"name": " New Infra ", "scope": ""})
    entity = Entity.objects.get()
    assert response.status_code == 302
    assert response.url == f"/admin/tsosi/entity/{entity.pk}/change/"
    assert (entity.name, entity.raw_name) == ("New Infra", "New Infra")
    assert entity.scope is None
    assert not entity.added_in_hub_by.exists()
    tsosi_id = entity.identifiers.get()
    assert tsosi_id.registry_id == REGISTRY_TSOSI
    matching = IdentifierEntityMatching.objects.get(identifier=tsosi_id)
    assert (
        matching.comments
        == "Added in the admin by TSOSI admin admin@tsosi.org."
    )
    assert entity.history.get().history_user == admin_user
    signal.assert_not_called()
    # Its Hub's Public page tab is linked in the message
    page = client.get(response.url)
    assert f"/hub/{tsosi_id.value}?tab=page" in page.content.decode()


def test_add_from_identifier(client, registries, record_fetch, signal):
    response = client.post(
        ADD_URL,
        {"identifier": "https://ror.org/05abcde12", "scope": ENTITY_SCOPE_IN},
    )
    assert response.status_code == 302
    entity = Entity.objects.get()
    assert (entity.name, entity.country) == ("Open Infrastructure", "FR")
    assert entity.website == "https://infra.org"
    assert entity.scope == ENTITY_SCOPE_IN
    assert entity.identifiers.get(registry_id=REGISTRY_ROR).value == "05abcde12"
    signal.assert_called_once_with(None, registries=[REGISTRY_ROR])

    # The name entered replaces the record's
    Entity.objects.all().delete()
    client.post(ADD_URL, {"identifier": "05abcde12", "name": "OI"})
    assert Entity.objects.get().name == "OI"


def test_add_existing_identifier(client, registries, record_fetch, signal):
    """The organization with the ID, or its record's other ID, is shown."""
    existing = EntityFactory.create()
    IdentifierFactory.create(
        entity=existing, registry_id=REGISTRY_WIKIDATA, value="Q123"
    )
    for value in ["Q123", "05abcde12"]:
        response = client.post(ADD_URL, {"identifier": value})
        assert response.status_code == 302
        assert response.url == f"/admin/tsosi/entity/{existing.pk}/change/"
    assert Entity.objects.count() == 1
    signal.assert_not_called()


@pytest.mark.parametrize(
    "data, field, error",
    [
        ({}, "__all__", "Enter a ROR or Wikidata ID, or a name."),
        ({"name": "  "}, "__all__", "Enter a ROR or Wikidata ID, or a name."),
        (
            {"identifier": "not an id"},
            "identifier",
            "Enter a ROR ID, like 02feahw73, or a Wikidata ID, like Q42.",
        ),
        (
            {"identifier": "01zzzzz99"},
            "identifier",
            "No ROR record has this ID.",
        ),
    ],
)
def test_add_errors(client, registries, record_fetch, data, field, error):
    response = client.post(ADD_URL, data)
    assert response.status_code == 200
    assert form_errors(response)[field] == [error]
    assert not Entity.objects.exists()


def test_add_registry_unavailable(client, registries, mocker):
    mocker.patch(
        "tsosi.api.hub.organizations.fetch_organization_record",
        side_effect=RegistryError("down"),
    )
    response = client.post(ADD_URL, {"identifier": "05abcde12"})
    assert response.status_code == 200
    assert "couldn't be reached" in form_errors(response)["identifier"][0]
    assert not Entity.objects.exists()


def test_add_same_name(client, registries, signal):
    existing = EntityFactory.create(name="Other", short_name="NI")
    EntityName.objects.create(
        entity=existing,
        type="alias",
        value="New Infra",
        registry_id=REGISTRY_ROR,
    )
    for name in ["new infra", "ni"]:
        response = client.post(ADD_URL, {"name": name})
        assert response.status_code == 200
        [error] = form_errors(response)["name"]
        assert "Already in TSOSI" in error
        assert f"/admin/tsosi/entity/{existing.pk}/change/" in error
    assert Entity.objects.count() == 1

    response = client.post(
        ADD_URL, {"name": "New Infra", "create_anyway": "on"}
    )
    assert response.status_code == 302
    assert Entity.objects.count() == 2
