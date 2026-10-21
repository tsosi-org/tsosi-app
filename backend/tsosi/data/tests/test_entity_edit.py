import io
import json
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from tsosi.data.entity_edit import sanitize_description
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import IdentifierEntityMatching, Membership
from tsosi.models.membership import MEMBERSHIP_STATUS_REVOKED
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

from .factories import EntityFactory, IdentifierFactory


@pytest.fixture(autouse=True)
def no_jobs(settings):
    settings.TSOSI_TRIGGER_JOBS = False


def edit_url(entity) -> str:
    return f"/api/entities/{entity.id}/edit/"


def member_client(entity, email: str = "member@uni.edu", **kwargs):
    """
    Return a client logged in as a member of the entity, and the member.
    """
    user = get_user_model().objects.create_user(username=email, email=email)
    Membership.objects.create(user=user, entity=entity, **kwargs)
    client = APIClient()
    client.force_login(user)
    return client, user


def png_file() -> SimpleUploadedFile:
    content = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(content, format="PNG")
    return SimpleUploadedFile(
        "logo.png", content.getvalue(), content_type="image/png"
    )


@pytest.mark.django_db
def test_edit_permissions(registries, admin_user):
    entity = EntityFactory.create(is_recipient=True)
    other_entity = EntityFactory.create(is_recipient=True)
    data = {"short_name": "E"}
    client, _ = member_client(entity)

    assert client.patch(edit_url(entity), data).status_code == 200
    # Members only edit their organization
    assert client.patch(edit_url(other_entity), data).status_code == 403
    assert APIClient().patch(edit_url(entity), data).status_code == 403
    assert client.patch("/api/entities/unknown/edit/", data).status_code == 404

    # An organization not on the public site yet can be edited, in preview
    hidden = EntityFactory.create()
    hidden_client, hidden_member = member_client(hidden, "hidden@uni.edu")
    assert hidden_client.patch(edit_url(hidden), data).status_code == 200

    hidden_member.memberships.update(status=MEMBERSHIP_STATUS_REVOKED)
    assert hidden_client.patch(edit_url(hidden), data).status_code == 403

    # The TSOSI team edits every organization
    staff_client = APIClient()
    staff_client.force_login(admin_user)
    for e in [entity, other_entity, hidden]:
        assert staff_client.patch(edit_url(e), data).status_code == 200


@pytest.mark.django_db
def test_edit_by_admin(registries):
    # A TSOSI admin, whose account may have no e-mail
    admin = get_user_model().objects.create_superuser(
        username="admin", email="", password=None
    )
    entity = EntityFactory.create(is_recipient=True)
    client = APIClient()
    client.force_login(admin)
    data = {"identifiers": {"wikidata": "Q42"}}
    response = client.patch(edit_url(entity), data, format="json")
    assert response.status_code == 200, response.data
    matching = IdentifierEntityMatching.objects.get(identifier__value="Q42")
    assert matching.comments == "Entity edit by TSOSI admin admin."


@pytest.mark.django_db
def test_edit_csrf(registries):
    entity = EntityFactory.create(is_recipient=True)
    _, user = member_client(entity)
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    data = {"short_name": "E"}
    assert client.patch(edit_url(entity), data).status_code == 403
    client.get("/api/hub/me")
    csrf_token = client.cookies["csrftoken"].value
    response = client.patch(edit_url(entity), data, HTTP_X_CSRFTOKEN=csrf_token)
    assert response.status_code == 200


@pytest.mark.django_db
def test_edit_entity(registries):
    entity = EntityFactory.create(
        is_recipient=True,
        name="Old name",
        country="FR",
        wikipedia_url="https://en.wikipedia.org/wiki/Old",
        wikipedia_extract="Old extract",
    )
    ror_id = IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_ROR, value="02rx3b187"
    )
    client, user = member_client(entity)

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
    response = client.patch(edit_url(entity), data, format="json")
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

    # The edit is in the history, with its user
    assert entity.history.filter(name="Old name").exists()
    assert entity.history.latest().history_user == user
    infra_history = entity.infrastructure_details.history.latest()
    assert infra_history.history_user == user
    assert infra_history.support_url == "https://support.org"
    # The new identifier is traced by its matching
    matching = IdentifierEntityMatching.objects.get(identifier__value="Q42")
    assert user.email in matching.comments

    # Clearing a value removes it from the TSOSI record
    response = client.patch(edit_url(entity), {"country": ""}, format="json")
    assert response.status_code == 200, response.data
    tsosi_id.refresh_from_db()
    assert "country" not in tsosi_id.current_version.value
    assert tsosi_id.current_version.value["name"] == "New name"

    # An edit without changes adds no history record
    history_count = entity.history.count()
    response = client.patch(
        edit_url(entity), {"name": "New name"}, format="json"
    )
    assert response.status_code == 200, response.data
    assert entity.history.count() == history_count


@pytest.mark.django_db
def test_edit_entity_validation(registries):
    entity = EntityFactory.create(is_recipient=True)
    other_entity = EntityFactory.create(is_recipient=True)
    IdentifierFactory.create(
        entity=other_entity, registry_id=REGISTRY_ROR, value="02rx3b187"
    )
    IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_WIKIDATA, value="Q1"
    )
    client, _ = member_client(entity)
    history_count = entity.history.count()

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
    assert entity.history.count() == history_count


@pytest.mark.django_db
def test_edit_entity_logo(registries, storage):
    entity = EntityFactory.create(is_recipient=True)
    client, _ = member_client(entity)

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

    # Replacing the logo keeps the previous file
    old_logo = entity.logo.name
    response = client.patch(
        edit_url(entity), {"logo": png_file()}, format="multipart"
    )
    assert response.status_code == 200, response.data
    entity.refresh_from_db()
    assert entity.logo.name != old_logo
    assert entity.logo.storage.exists(old_logo)
    # It's referenced in the entity's history
    assert entity.history.filter(logo=old_logo).exists()

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
