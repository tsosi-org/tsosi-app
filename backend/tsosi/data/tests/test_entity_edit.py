import io
import json
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from tsosi.data.edit_access import grant_edit_access
from tsosi.data.entity_edit import sanitize_description
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import EntityEditAccess, EntityEditLog
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

from .factories import EntityFactory, IdentifierFactory


@pytest.fixture(autouse=True)
def no_jobs(settings):
    settings.TSOSI_TRIGGER_JOBS = False


def edit_url(entity) -> str:
    return f"/api/entities/{entity.id}/edit/"


def client_with_key(key: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {key}")
    return client


def png_file() -> SimpleUploadedFile:
    content = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(content, format="PNG")
    return SimpleUploadedFile(
        "logo.png", content.getvalue(), content_type="image/png"
    )


@pytest.mark.django_db
def test_grant_edit_access(registries):
    entity = EntityFactory.create()
    access, url = grant_edit_access(entity, "someone@example.org", days=3)

    assert url.startswith(f"http://localhost:5173/entities/{entity.id}#edit=")
    key = url.split("#edit=")[1]
    # Only the hash is stored
    assert access.key_hash != key
    assert EntityEditAccess.objects.get_by_key(key) == access

    admin_access, url = grant_edit_access(None, "admin@example.org")
    assert url.startswith("http://localhost:5173/#edit=")
    # Admin accesses are short-lived by default
    assert admin_access.date_expires - timezone.now() <= timedelta(days=1)

    # The grantee e-mail is optional
    access, _ = grant_edit_access(entity)
    assert access.email is None
    assert access.grantee == f"edit access #{access.id}"


@pytest.mark.django_db
def test_edit_access_check(registries):
    entity = EntityFactory.create()
    other_entity = EntityFactory.create()
    _, key = EntityEditAccess.create_with_key(entity, "a@example.org", 1)
    expired, expired_key = EntityEditAccess.create_with_key(
        entity, "b@example.org", 1
    )
    expired.date_expires = timezone.now() - timedelta(minutes=1)
    expired.save()

    assert client_with_key(key).get(edit_url(entity)).status_code == 200
    assert APIClient().get(edit_url(entity)).status_code == 403
    assert client_with_key("wrong").get(edit_url(entity)).status_code == 403
    assert client_with_key(expired_key).get(edit_url(entity)).status_code == 403
    # The key is only valid for its entity
    assert client_with_key(key).get(edit_url(other_entity)).status_code == 403
    # An admin key is valid for all entities
    _, admin_key = EntityEditAccess.create_with_key(None, "c@example.org", 1)
    for e in [entity, other_entity]:
        assert client_with_key(admin_key).get(edit_url(e)).status_code == 200


@pytest.mark.django_db
def test_edit_entity(registries):
    entity = EntityFactory.create(
        name="Old name",
        country="FR",
        wikipedia_url="https://en.wikipedia.org/wiki/Old",
        wikipedia_extract="Old extract",
    )
    ror_id = IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_ROR, value="02rx3b187"
    )
    access, key = EntityEditAccess.create_with_key(entity, "a@example.org", 1)

    data = {
        "name": "New name",
        "short_name": "NN",
        "country": "DE",
        "date_inception": "2001-02-03",
        "description": "Hello <a href='https://x.org' onclick='x()'>x</a>"
        "<script>alert(1)</script>",
        "is_barcelona": True,
        "website": "https://new.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/New",
        "identifiers": {
            # Unchanged identifier
            "ror": "https://ror.org/02rx3b187",
            "wikidata": "https://www.wikidata.org/wiki/Q42",
        },
        "infrastructure": {
            "support_url": "https://support.org",
            "posi_url": "",
            "infra_finder_url": None,
            "date_scoss_start": "2020-01-01",
            "date_scoss_end": "2022-01-01",
        },
    }
    response = client_with_key(key).patch(edit_url(entity), data, format="json")
    assert response.status_code == 200, response.data

    entity.refresh_from_db()
    assert entity.name == "New name"
    assert entity.short_name == "NN"
    assert entity.country == "DE"
    assert entity.date_inception == date(2001, 2, 3)
    assert entity.description == (
        'Hello <a href="https://x.org" rel="noopener noreferrer">x</a>'
    )
    assert entity.is_barcelona
    assert entity.website == "https://new.org"
    assert entity.wikipedia_url == "https://en.wikipedia.org/wiki/New"
    # The extract of the previous page is dropped
    assert entity.wikipedia_extract is None
    assert entity.is_scoss
    assert entity.infrastructure_details.support_url == "https://support.org"
    assert entity.infrastructure_details.posi_url is None

    # Identifiers
    assert entity.identifiers.get(registry_id=REGISTRY_ROR) == ror_id
    assert entity.identifiers.get(registry_id=REGISTRY_WIKIDATA).value == "Q42"

    # The manual values are stored in the TSOSI record
    tsosi_id = entity.identifiers.get(registry_id=REGISTRY_TSOSI)
    record = tsosi_id.current_version.value
    assert record["name"] == "New name"
    assert record["country"] == "DE"
    assert record["date_inception"] == "2001-02-03"
    assert record["wikipedia_url"] == "https://en.wikipedia.org/wiki/New"

    log = EntityEditLog.objects.get(entity=entity)
    assert log.access == access
    assert log.changes["name"] == {"old": "Old name", "new": "New name"}
    assert "identifiers.ror" not in log.changes
    assert log.changes["identifiers.wikidata"] == {"old": None, "new": "Q42"}

    # Clearing a value removes it from the TSOSI record
    response = client_with_key(key).patch(
        edit_url(entity), {"country": ""}, format="json"
    )
    assert response.status_code == 200, response.data
    tsosi_id.refresh_from_db()
    assert "country" not in tsosi_id.current_version.value
    assert tsosi_id.current_version.value["name"] == "New name"


@pytest.mark.django_db
def test_edit_entity_validation(registries):
    entity = EntityFactory.create()
    other_entity = EntityFactory.create()
    IdentifierFactory.create(
        entity=other_entity, registry_id=REGISTRY_ROR, value="02rx3b187"
    )
    IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_WIKIDATA, value="Q1"
    )
    _, key = EntityEditAccess.create_with_key(entity, "a@example.org", 1)
    client = client_with_key(key)

    invalid_payloads = [
        {"name": ""},
        {"country": "France"},
        {"website": "not an url"},
        {"wikipedia_url": "https://example.org/wiki/Page"},
        {"identifiers": {"ror": "not-a-ror"}},
        # Identifier attached to another entity
        {"identifiers": {"ror": "02rx3b187"}},
        # Existing identifiers can't be changed nor removed
        {"identifiers": {"wikidata": "Q2"}},
        {"identifiers": {"wikidata": None}},
        {"identifiers": {"wikidata": ""}},
        {"infrastructure": {"support_url": "not an url"}},
        {
            "infrastructure": {
                "date_scoss_start": "2022-01-01",
                "date_scoss_end": None,
            }
        },
        {
            "infrastructure": {
                "date_scoss_start": "2022-01-01",
                "date_scoss_end": "2020-01-01",
            }
        },
    ]
    for payload in invalid_payloads:
        response = client.patch(edit_url(entity), payload, format="json")
        assert response.status_code == 400, payload
    assert not EntityEditLog.objects.exists()


@pytest.mark.django_db
def test_edit_entity_logo(registries, storage):
    entity = EntityFactory.create()
    _, key = EntityEditAccess.create_with_key(entity, "a@example.org", 1)
    client = client_with_key(key)

    response = client.patch(
        edit_url(entity),
        {
            "data": json.dumps({"short_name": "E"}),
            "logo": png_file(),
            "icon": png_file(),
        },
        format="multipart",
    )
    assert response.status_code == 200, response.data
    entity.refresh_from_db()
    assert entity.short_name == "E"
    assert entity.logo
    assert entity.manual_logo
    assert entity.icon

    # Replacing the logo keeps the previous file, referenced in the edit log
    old_logo = entity.logo.name
    response = client.patch(
        edit_url(entity), {"logo": png_file()}, format="multipart"
    )
    assert response.status_code == 200, response.data
    entity.refresh_from_db()
    assert entity.logo.name != old_logo
    assert entity.logo.storage.exists(old_logo)
    log = EntityEditLog.objects.filter(entity=entity).latest("id")
    assert log.changes["logo"] == {"old": old_logo, "new": entity.logo.name}

    not_an_image = SimpleUploadedFile("logo.png", b"not an image")
    response = client.patch(
        edit_url(entity), {"logo": not_an_image}, format="multipart"
    )
    assert response.status_code == 400


def test_sanitize_description():
    assert sanitize_description("  ") is None
    assert sanitize_description("<p>a <b>b</b></p>") == "<p>a <b>b</b></p>"
    assert (
        sanitize_description('<a href="javascript:alert(1)">x</a>')
        == '<a rel="noopener noreferrer">x</a>'
    )
    assert sanitize_description("<img src=x onerror=alert(1)>") is None
