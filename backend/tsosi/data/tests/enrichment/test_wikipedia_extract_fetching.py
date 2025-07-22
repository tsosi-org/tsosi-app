from datetime import UTC, datetime, timedelta

import pytest
from tsosi.data.enrichment.api_related import (
    entities_for_wikipedia_extract_update,
    update_wikipedia_extract,
)
from tsosi.models.entity import (
    ENTITY_REQUEST_WIKIMEDIA_LOGO,
    ENTITY_REQUEST_WIKIPEDIA_EXTRACT,
    EntityRequest,
)

from ..factories import EntityFactory, EntityRequestFactory


@pytest.mark.django_db
def test_entities_for_wikipedia_update():
    print("Testing selection of entities for wikipedia extract update.")
    entity = EntityFactory.create(
        wikipedia_url="https://en.wikipedia.org/wiki/Grenoble_Alpes_University"
    )
    # Default
    entities = entities_for_wikipedia_extract_update(query_threshold=3)
    assert len(entities) == 1
    assert entities.iloc[0].id == entity.id

    # Recently fetched extract
    now = datetime.now(UTC)
    entity.date_wikipedia_fetched = now
    entity.save()
    entities = entities_for_wikipedia_extract_update(query_threshold=2)
    assert entities.empty

    # Old fetched extract
    entity.date_wikipedia_fetched = now - timedelta(days=30)
    entity.save()
    entities = entities_for_wikipedia_extract_update(query_threshold=2)
    assert len(entities) == 1
    assert entities.iloc[0].id == entity.id

    # Already attempted fetch - OK
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIPEDIA_EXTRACT
    )
    entities = entities_for_wikipedia_extract_update(query_threshold=2)
    assert len(entities) == 1
    assert entities.iloc[0].id == entity.id

    # Already attempted fetch - OK (different requests)
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIMEDIA_LOGO
    )
    entities = entities_for_wikipedia_extract_update(query_threshold=2)
    assert len(entities) == 1
    assert entities.iloc[0].id == entity.id

    # Already attempted fetch - exceeding max. retries
    EntityRequestFactory.create(
        entity=entity, timestamp=now, type=ENTITY_REQUEST_WIKIPEDIA_EXTRACT
    )
    entities = entities_for_wikipedia_extract_update(query_threshold=2)
    assert entities.empty

    # Ensure it's bc of the max retry
    entities = entities_for_wikipedia_extract_update(query_threshold=3)
    assert len(entities) == 1
    assert entities.iloc[0].id == entity.id


@pytest.fixture
def wiki_fetch_setting(settings):
    settings.TSOSI_WIKI_FETCH_RETRY = 2


@pytest.mark.django_db
def test_update_wikipedia_extract():
    """TODO: Mock the call to Wikipedia API."""
    print("Testing the update of wikipedia extract.")
    entity = EntityFactory.create(
        wikipedia_url="https://en.wikipedia.org/wiki/Grenoble_Alpes_University"
    )
    e_requests = EntityRequest.objects.all()
    assert entity.wikipedia_extract is None
    assert entity.date_wikipedia_fetched is None
    assert len(e_requests) == 0

    res = update_wikipedia_extract(use_tokens=False)
    entity.refresh_from_db()
    e_requests = EntityRequest.objects.all()
    assert not res.partial
    assert entity.wikipedia_extract is not None
    assert entity.date_wikipedia_fetched is not None
    assert len(e_requests) == 1
    assert e_requests[0].entity.id == entity.id


@pytest.mark.django_db
def test_update_corrupted_wikipedia_extract(wiki_fetch_setting):
    """TODO: Mock the call to Wikipedia API."""
    print("Testing the update of a wikipedia extract with a corrupted link.")
    entity = EntityFactory.create(
        wikipedia_url="https://en.wikipedia.org/wiki/Something_Here_is_Wrong_test"
    )
    e_requests = EntityRequest.objects.all()

    # Test default
    assert entity.wikipedia_extract is None
    assert entity.date_wikipedia_fetched is None
    assert len(e_requests) == 0

    # First attempt
    res = update_wikipedia_extract(use_tokens=False)
    entity.refresh_from_db()
    e_requests = EntityRequest.objects.all()
    assert res.partial
    assert entity.wikipedia_extract is None
    assert entity.date_wikipedia_fetched is None
    assert len(e_requests) == 1
    assert e_requests[0].entity.id == entity.id

    # Second attempt
    res = update_wikipedia_extract(use_tokens=False)
    e_requests = EntityRequest.objects.all()
    assert res.partial
    assert len(e_requests) == 2
    assert all(r.entity.id == entity.id for r in e_requests)

    # Third attempt - Exceeding max retry so no request is made
    res = update_wikipedia_extract(use_tokens=False)
    e_requests = EntityRequest.objects.all()
    assert not res.partial
    assert entity.wikipedia_extract is None
    assert entity.date_wikipedia_fetched is None
    assert len(e_requests) == 2
    assert all(r.entity.id == entity.id for r in e_requests)
