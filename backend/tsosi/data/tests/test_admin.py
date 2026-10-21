import pytest
from rest_framework.test import APIClient
from tsosi.models import EntityEditAccess
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK

from .factories import EntityFactory

ENTITY_ADMIN_URL = "/admin/tsosi/entity/"


@pytest.mark.django_db
def test_entities_to_check(admin_client):
    to_check = EntityFactory.create(scope=ENTITY_SCOPE_TO_CHECK)
    in_scope = EntityFactory.create(scope=ENTITY_SCOPE_IN)
    response = admin_client.get(
        ENTITY_ADMIN_URL, {"scope__exact": ENTITY_SCOPE_TO_CHECK}
    )
    assert response.status_code == 200
    entities = list(response.context["cl"].result_list)
    assert entities == [to_check]
    assert in_scope not in entities


@pytest.mark.django_db
def test_set_scope(admin_client, admin_user):
    entity = EntityFactory.create(scope=ENTITY_SCOPE_TO_CHECK)
    name = entity.name
    response = admin_client.post(
        f"{ENTITY_ADMIN_URL}{entity.id}/change/",
        {"scope": ENTITY_SCOPE_IN, "name": "Other name"},
    )
    assert response.status_code == 302
    entity.refresh_from_db()
    assert entity.scope == ENTITY_SCOPE_IN
    # Only the scope can be changed
    assert entity.name == name
    # The change is in the history, with the admin user
    assert entity.history.latest().history_user == admin_user


@pytest.mark.django_db
def test_no_entity_add_or_delete(admin_client):
    entity = EntityFactory.create()
    assert admin_client.get(f"{ENTITY_ADMIN_URL}add/").status_code == 403
    url = f"{ENTITY_ADMIN_URL}{entity.id}/delete/"
    assert admin_client.get(url).status_code == 403


@pytest.mark.django_db
def test_api_ignores_admin_session(registries, admin_user):
    """
    A Django admin session doesn't authenticate the API, so it doesn't
    require a CSRF token on the API's write requests.
    """
    entity = EntityFactory.create(is_recipient=True)
    _, key = EntityEditAccess.create_with_key(entity, "a@example.org", 1)
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {key}")
    response = client.patch(
        f"/api/entities/{entity.id}/edit/", {"short_name": "E"}, format="json"
    )
    assert response.status_code == 200, response.data
