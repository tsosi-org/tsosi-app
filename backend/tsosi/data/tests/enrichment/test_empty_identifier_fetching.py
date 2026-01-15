from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from tsosi.data.enrichment.api_related import (
    empty_identifiers,
    fetch_empty_identifier_records,
    log_identifier_requests,
)
from tsosi.models import IdentifierRequest, IdentifierVersion
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

from ..factories import (
    IdentifierFactory,
    IdentifierRequestFactory,
    IdentifierVersionFactory,
)
from ..utils import MockAiohttpResponse


@pytest.mark.django_db
def test_empty_identifier_selection(registries):
    print("Testing empty identifiers selection")
    identifier = IdentifierFactory.create(registry_id=REGISTRY_ROR)

    timestamp = datetime.now(UTC)
    r_1 = IdentifierRequestFactory.create(
        identifier=identifier, timestamp=timestamp
    )
    r_2 = IdentifierRequestFactory.create(
        identifier=identifier, timestamp=timestamp
    )

    data = empty_identifiers(query_threshold=3)
    assert len(data) == 1
    assert data["id"][0] == identifier.id

    data = empty_identifiers(query_threshold=2)
    assert data.empty

    # Test exceding time threshold
    new_timestamp = datetime.now(UTC) - timedelta(days=2)
    r_1.timestamp = new_timestamp
    r_1.save()

    data = empty_identifiers(query_threshold=2)
    assert len(data) == 1
    assert data["id"][0] == identifier.id


@pytest.mark.django_db
def test_empty_identifier_no_version(registries):
    print("Testing empty identifiers with/out version")
    identifier = IdentifierFactory.create(registry_id=REGISTRY_ROR)

    data = empty_identifiers(query_threshold=None)
    assert len(data) == 1
    assert data["id"][0] == identifier.id

    # Test no results with a defined IdentifierVersion
    id_version = IdentifierVersionFactory.create(identifier=identifier)
    identifier.current_version = id_version
    identifier.save()
    data = empty_identifiers(query_threshold=None)
    assert data.empty


@pytest.mark.django_db
def test_log_identifier_requests(registries):
    print("Testing identifier requests logging")
    id_1 = IdentifierFactory.create(registry_id=REGISTRY_ROR)
    id_2 = IdentifierFactory.create(registry_id=REGISTRY_WIKIDATA)

    id_requests = IdentifierRequest.objects.all()
    assert len(id_requests) == 0

    ts = datetime.now(UTC)
    log_data = pd.DataFrame(
        [
            {
                "identifier_id": id_1.id,
                "info": "https://some.url",
                "timestamp": ts,
                "http_status": 200,
                "error": False,
                "error_msg": None,
            },
            {
                "identifier_id": id_2.id,
                "info": "https://some.url",
                "timestamp": ts,
                "http_status": 429,
                "error": True,
                "error_msg": "TOO MANY REQUESTS",
            },
        ]
    )
    log_identifier_requests(log_data)
    id_requests = IdentifierRequest.objects.all()
    assert len(id_requests) == 2


@pytest.mark.django_db
def test_fetch_empty_identifier_records(registries, mocker, uga_ror_record):
    print("Testing correct fetching of empty ROR identifier")
    # ROR UGA - https://ror.org/02rx3b187

    id_1 = IdentifierFactory.create(registry_id=REGISTRY_ROR, value="02rx3b187")

    # Test table is empty on init
    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 0

    # Patch the HTTP call
    resp = MockAiohttpResponse(json=uga_ror_record)
    mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Actual test
    _ = fetch_empty_identifier_records(REGISTRY_ROR, use_tokens=False)

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 1
    assert versions[0].identifier.id == id_1.id

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 1
    assert requests[0].identifier.id == id_1.id
    assert not requests[0].error


@pytest.fixture
def identifier_fetch_setting(settings):
    settings.TSOSI_IDENTIFIER_FETCH_RETRY = 2


@pytest.mark.django_db
def test_fetch_corrupted_empty_ror_records(
    registries, identifier_fetch_setting, mocker
):
    print("Testing fetching error of corrupted empty ROR identifier")
    # Non-existent ROR - https://ror.org/a00000000
    id_1 = IdentifierFactory.create(registry_id=REGISTRY_ROR, value="000000000")

    # Test table is empty on init
    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 0

    # Patch the HTTP call
    resp = MockAiohttpResponse(status=404, json={"errors": ["unvalid"]})
    mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # First try
    result = fetch_empty_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 1
    assert requests[0].identifier.id == id_1.id
    assert requests[0].error
    assert requests[0].http_status == 404

    # Second try
    result = fetch_empty_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2
    assert all(r.identifier.id == id_1.id for r in requests)
    assert all(r.error for r in requests)

    # Third try - no fetching performed because threshold was met.
    # Result should not be partial
    result = fetch_empty_identifier_records(REGISTRY_ROR, use_tokens=False)
    assert not result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2


@pytest.mark.django_db
def test_fetch_corrupted_empty_wikidata_records(
    registries, identifier_fetch_setting
):
    print("Testing fetching error of corrupted empty Wikidata identifier")
    # Invalid Wikidata
    id_1 = IdentifierFactory.create(
        registry_id=REGISTRY_WIKIDATA, value="QINCORRECT_VALUE"
    )

    # Test table is empty on init
    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 0

    # First try
    result = fetch_empty_identifier_records(REGISTRY_WIKIDATA, use_tokens=False)
    assert result.partial == True

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 1
    assert requests[0].identifier.id == id_1.id
    assert requests[0].error

    # Second try
    result = fetch_empty_identifier_records(REGISTRY_WIKIDATA, use_tokens=False)
    assert result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2
    assert all(r.identifier.id == id_1.id for r in requests)
    assert all(r.error for r in requests)

    # Third try - no fetching performed because threshold was met.
    # Result should not be partial
    result = fetch_empty_identifier_records(REGISTRY_WIKIDATA, use_tokens=False)
    assert not result.partial

    versions = IdentifierVersion.objects.all()
    assert len(versions) == 0

    requests = IdentifierRequest.objects.all()
    assert len(requests) == 2
    assert all(r.identifier.id == id_1.id for r in requests)
    assert all(r.error for r in requests)
