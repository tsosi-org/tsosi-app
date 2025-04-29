from datetime import UTC, datetime

import pytest
from tsosi.data.enrichment.database_related import (
    clean_identifier_versions,
    identifier_versions_for_cleaning,
)
from tsosi.models import Identifier, IdentifierVersion

from ..factories import IdentifierFactory, IdentifierVersionFactory


@pytest.mark.django_db
def test_identifier_versions_for_cleaning(registries):
    print("Testing the selection of identifier versions for cleaning.")
    id_1 = IdentifierFactory.create()
    id_2 = IdentifierFactory.create()
    id_1_v_1 = IdentifierVersionFactory.create(
        identifier=id_1,
        date_start=datetime(year=2020, month=1, day=1, tzinfo=UTC),
    )
    id_2_v_1 = IdentifierVersionFactory.create(
        identifier=id_2,
        date_start=datetime(year=2020, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2021, month=1, day=1, tzinfo=UTC),
    )
    id_2_v_2 = IdentifierVersionFactory.create(
        identifier=id_2,
        date_start=datetime(year=2021, month=1, day=1, tzinfo=UTC),
    )

    versions = identifier_versions_for_cleaning()

    assert len(versions) == 2
    assert len(versions[versions["identifier_id"] == id_2.id]) == 2
    assert id_2_v_1.id in versions["id"].to_list()
    assert id_2_v_2.id in versions["id"].to_list()


@pytest.mark.django_db
def test_clean_identifier_versions(registries):
    print("Testing the cleaning of identifier versions.")
    id_1 = IdentifierFactory.create()
    id_2 = IdentifierFactory.create()
    record_v_1 = {
        "names": [
            {
                "value": "Université Joseph Fourier",
                "types": ["ror_display"],
            }
        ]
    }
    record_v_2 = {
        "names": [
            {
                "value": "Université Grenoble Alpes",
                "types": ["ror_display"],
            }
        ]
    }
    record_v_3 = {
        "names": [
            {
                "value": "Université Grenoble Futur",
                "types": ["ror_display"],
            }
        ]
    }
    # Record V1
    id_v_1 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_1,
        date_start=datetime(year=2020, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2021, month=1, day=1, tzinfo=UTC),
    )
    id_v_2 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_1,
        date_start=datetime(year=2021, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2022, month=1, day=1, tzinfo=UTC),
    )
    id_v_3 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_1,
        date_start=datetime(year=2022, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2023, month=1, day=1, tzinfo=UTC),
    )
    # Record V2
    id_v_4 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_2,
        date_start=datetime(year=2023, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2024, month=1, day=1, tzinfo=UTC),
    )
    # Record V3
    id_v_5 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_3,
        date_start=datetime(year=2024, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2025, month=1, day=1, tzinfo=UTC),
    )
    id_v_6 = IdentifierVersionFactory.create(
        identifier=id_1,
        value=record_v_3,
        date_start=datetime(year=2025, month=1, day=1, tzinfo=UTC),
    )
    id_1.current_version = id_v_6
    id_1.save()

    # ID 1 V1
    id_2_v_1 = IdentifierVersionFactory.create(
        identifier=id_2,
        value=record_v_1,
        date_start=datetime(year=2024, month=1, day=1, tzinfo=UTC),
        date_end=datetime(year=2025, month=1, day=1, tzinfo=UTC),
    )
    id_2_v_2 = IdentifierVersionFactory.create(
        identifier=id_2,
        value=record_v_2,
        date_start=datetime(year=2025, month=1, day=1, tzinfo=UTC),
    )
    id_2.current_version = id_2_v_2
    id_2.save()

    clean_identifier_versions()

    versions = IdentifierVersion.objects.all().order_by("date_created")
    assert len(versions) == 5

    v_1 = versions[0]
    assert v_1.id == id_v_1.id
    assert v_1.date_start == datetime(year=2020, month=1, day=1, tzinfo=UTC)
    assert v_1.date_end == datetime(year=2023, month=1, day=1, tzinfo=UTC)

    v_2 = versions[1]
    assert v_2.id == id_v_4.id
    assert v_2.date_start == datetime(year=2023, month=1, day=1, tzinfo=UTC)
    assert v_2.date_end == datetime(year=2024, month=1, day=1, tzinfo=UTC)

    v_3 = versions[2]
    assert v_3.id == id_v_5.id
    assert v_3.date_start == datetime(year=2024, month=1, day=1, tzinfo=UTC)
    assert v_3.date_end is None

    id_1 = Identifier.objects.get(id=id_1.id)
    assert id_1.current_version == id_v_5

    v_4 = versions[3]
    assert v_4.id == id_2_v_1.id
    assert v_4.date_start == id_2_v_1.date_start
    assert v_4.date_end == id_2_v_1.date_end

    v_5 = versions[4]
    assert v_5.id == id_2_v_2.id
    assert v_5.date_start == id_2_v_2.date_start
    assert v_5.date_end is None

    id_2 = Identifier.objects.get(id=id_2.id)
    assert id_2.current_version == id_2_v_2
