from datetime import UTC, datetime, timedelta

import pytest
from tsosi.data.enrichment.api_related import (
    entities_for_logo_update,
    update_logos,
)
from tsosi.models.entity import (
    ENTITY_REQUEST_WIKIMEDIA_LOGO,
    ENTITY_REQUEST_WIKIPEDIA_EXTRACT,
    Entity,
    EntityRequest,
)

from ..factories import EntityFactory, EntityRequestFactory


@pytest.mark.django_db
def test_entities_for_logo_update():
    print("Testing selection of entities for logo update.")
    entity = EntityFactory.create(
        logo_url="http://commons.wikimedia.org/wiki/Special:FilePath/Logo%20Universit%C3%A9%20Grenoble-Alpes%20%282020%29.jpg"
    )
    # Default
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 1
    assert entities[0].id == entity.id

    # Recently fetched extract
    now = datetime.now(UTC)
    entity.date_logo_fetched = now
    entity.save()
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 0

    # Old extract
    entity.date_logo_fetched = now - timedelta(days=30)
    entity.save()
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 1
    assert entities[0].id == entity.id

    # Already attempted fetch - OK
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIMEDIA_LOGO
    )
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 1
    assert entities[0].id == entity.id

    # Already attempted fetch - OK (different requests)
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIPEDIA_EXTRACT
    )
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 1
    assert entities[0].id == entity.id

    # Already attempted fetch - exceeding max. retries
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIMEDIA_LOGO
    )
    entities = entities_for_logo_update(query_threshold=2)
    assert len(entities) == 0

    # Ensure it's bc of the max retry
    entities = entities_for_logo_update(query_threshold=3)
    assert len(entities) == 1
    assert entities[0].id == entity.id


@pytest.fixture
def wiki_fetch_setting(settings):
    settings.TSOSI_WIKI_FETCH_RETRY = 2


@pytest.mark.django_db
def test_update_logo(storage):
    """TODO: Mock the call to Wikimedia API."""
    print("Testing selection of entities for logo update.")
    entity = EntityFactory.create(
        logo_url="http://commons.wikimedia.org/wiki/Special:FilePath/Logo%20Universit%C3%A9%20Grenoble-Alpes%20%282020%29.jpg"
    )
    e_requests = EntityRequest.objects.all()
    assert not entity.logo
    assert entity.date_logo_fetched is None
    assert len(e_requests) == 0

    res = update_logos(use_tokens=False)
    entity = Entity.objects.get(pk=entity.pk)
    e_requests = EntityRequest.objects.all()
    assert not res.partial
    assert entity.logo
    assert entity.date_logo_fetched is not None
    assert len(e_requests) == 1
    assert e_requests[0].entity.id == entity.id


@pytest.fixture
def wiki_logo_retry(settings):
    settings.TSOSI_WIKI_FETCH_RETRY = 2


@pytest.mark.django_db
def test_update_corrupted_logo(storage, wiki_logo_retry):
    """TODO: Mock the call to Wikimedia API."""
    print("Testing the update of a logo with a corrupted url.")
    entity = EntityFactory.create(
        logo_url="http://commons.wikimedia.org/wiki/Special:FilePath/What_is_this_extension.jpff"
    )
    e_requests = EntityRequest.objects.all()

    # Test default
    assert not entity.logo
    assert entity.date_logo_fetched is None
    assert len(e_requests) == 0

    # First attempt
    res = update_logos(use_tokens=False)
    entity = Entity.objects.get(pk=entity.pk)
    e_requests = EntityRequest.objects.all()
    assert res.partial
    assert not entity.logo
    assert entity.date_logo_fetched is None
    assert len(e_requests) == 1
    assert e_requests[0].entity.id == entity.id

    # Second attempt
    res = update_logos(use_tokens=False)
    entity = Entity.objects.get(pk=entity.pk)
    e_requests = EntityRequest.objects.all()
    assert res.partial
    assert len(e_requests) == 2
    assert all(r.entity.id == entity.id for r in e_requests)

    # Third attempt - Exceeding max retry so no request is made
    res = update_logos(use_tokens=False)
    entity = Entity.objects.get(pk=entity.pk)
    e_requests = EntityRequest.objects.all()
    assert not res.partial
    assert not entity.logo
    assert entity.date_logo_fetched is None
    assert len(e_requests) == 2
