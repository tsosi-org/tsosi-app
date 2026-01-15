from datetime import UTC, datetime, timedelta

import pytest
from tsosi.data.enrichment.api_related import (
    identifiers_for_refresh,
    refresh_identifier_records,
)
from tsosi.models import IdentifierRequest, IdentifierVersion
from tsosi.models.static_data import REGISTRY_ROR

from ..factories import (
    IdentifierFactory,
    IdentifierRequestFactory,
    IdentifierVersionFactory,
)
from ..utils import MockAiohttpResponse


@pytest.mark.django_db
def test_identifiers_for_refresh(registries):
    print("Testing selection of identifiers for refresh.")
    identifier = IdentifierFactory.create()
    now = datetime.now(UTC)

    # Don't select identifer without a version
    ids = identifiers_for_refresh(identifier.registry_id, query_threshold=2)
    assert ids.empty

    # Identifier with recent version
    id_version = IdentifierVersionFactory.create(
        identifier=identifier, date_last_fetched=now
    )
    identifier.current_version = id_version
    identifier.save()
    ids = identifiers_for_refresh(identifier.registry_id, query_threshold=2)
    assert ids.empty

    # Identifier with old version
    id_version.date_last_fetched = now - timedelta(days=30)
    id_version.save()
    ids = identifiers_for_refresh(identifier.registry_id, query_threshold=2)
    assert len(ids) == 1
    assert ids["id"][0] == identifier.id

    # Already attempted fetch
    r_1 = IdentifierRequestFactory.create(identifier=identifier, timestamp=now)
    r_2 = IdentifierRequestFactory.create(identifier=identifier, timestamp=now)
    ids = identifiers_for_refresh(identifier.registry_id, query_threshold=2)
    assert ids.empty

    ids = identifiers_for_refresh(identifier.registry_id, query_threshold=3)
    assert len(ids) == 1
    assert ids["id"][0] == identifier.id


@pytest.mark.django_db
def test_refresh_identifier_records(registries, mocker, uga_ror_record):
    print("Testing correct refresh of identifier records.")
    # ROR UGA - https://ror.org/02rx3b187
    id_1 = IdentifierFactory.create(registry_id=REGISTRY_ROR, value="02rx3b187")

    a_while_ago = datetime.now(UTC) - timedelta(days=30)
    id_v_1 = IdentifierVersionFactory.create(
        identifier=id_1,
        value={"NOT_FROM_ROR": True},
        date_start=a_while_ago,
        date_last_fetched=a_while_ago,
    )
    assert id_v_1.date_end is None

    id_1.current_version = id_v_1
    id_1.save()

    # Patch the HTTP call
    resp = MockAiohttpResponse(json=uga_ror_record)
    mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Actual test
    result = refresh_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert not result.partial

    id_v_1.refresh_from_db()
    id_1.refresh_from_db()
    versions = IdentifierVersion.objects.all().order_by("date_start")
    assert len(versions) == 2
    assert versions[0] == id_v_1
    assert id_v_1.date_end is not None
    id_v_2 = versions[1]
    assert id_v_2.identifier == id_1
    assert id_v_2.date_end is None
    assert id_v_2 == id_1.current_version

    # Try again when the record should not have changed.
    # Only the date_last_fetched should be updated
    c_date = datetime.now(UTC)
    id_v_2.date_last_fetched = a_while_ago
    id_v_2.save()

    result = refresh_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert not result.partial

    id_1.refresh_from_db()
    id_v_2.refresh_from_db()
    versions = IdentifierVersion.objects.all().order_by("date_start")
    assert len(versions) == 2
    assert versions[1] == id_v_2
    assert id_v_2.date_last_fetched > c_date
    assert id_v_2 == id_1.current_version

    reqs = IdentifierRequest.objects.all()
    assert len(reqs) == 2
    assert all(r.identifier == id_1 for r in reqs)


@pytest.fixture
def identifier_fetch_setting(settings):
    settings.TSOSI_IDENTIFIER_FETCH_RETRY = 2


@pytest.mark.django_db
def test_refresh_corrupted_ror_record(
    registries, identifier_fetch_setting, mocker, uga_ror_record
):
    print("Testing fetching error of corrupted ROR identifier.")
    # Non-existent ROR - https://ror.org/000000000
    id_1 = IdentifierFactory.create(registry_id=REGISTRY_ROR, value="000000000")
    a_while_ago = datetime.now(UTC) - timedelta(days=30)
    id_v_1 = IdentifierVersionFactory.create(
        identifier=id_1,
        value={"NOT_FROM_ROR": True},
        date_start=a_while_ago,
        date_last_fetched=a_while_ago,
    )
    assert id_v_1.date_end is None

    id_1.current_version = id_v_1
    id_1.save()

    # Patch the HTTP call
    resp = MockAiohttpResponse(status=404, json={"errors": ["unvalid"]})
    mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # First try
    result = refresh_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 1
    assert versions[0] == id_v_1

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 1
    assert requests[0].identifier.id == id_1.id
    assert requests[0].error
    assert requests[0].http_status == 404

    # Second try
    result = refresh_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 1

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2
    assert all(r.identifier.id == id_1.id for r in requests)
    assert all(r.error for r in requests)

    # Third try - no fetching performed because threshold was met.
    # Result should not be partial
    result = refresh_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert not result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 1

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2
