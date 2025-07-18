import datetime

import pytest
import tsosi.data.preparation.raw_data_config as dc
from tsosi.data.ingestion.core import validate_data_load_source
from tsosi.models import DataLoadSource

from ..factories import DataLoadSourceFactory


@pytest.mark.django_db
def test_data_load_empty_db(datasources):
    print("Testing the validation of a new data load with an empty database.")
    test = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
    )
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    test.full_data = True
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    test.year = 2025
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    test.full_data = False
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0


@pytest.mark.django_db
def test_data_load_non_empty_db(datasources):
    print(
        "Testing the validation of a new data load with a non-empty database."
    )
    dls = DataLoadSourceFactory.create(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
        year=2020,
    )
    test = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        year=2020,
        full_data=True,
    )
    # Same data load re-load
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 1
    assert oldies[0].pk == dls.pk

    # Ingesting additional data on a given year with an existing full one
    test.full_data = False
    valid, oldies = validate_data_load_source(test)
    assert not valid
    assert len(oldies) == 0

    # Ingesting additional data on a given year with no full one
    dls.full_data = False
    dls.save()
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    # Ingesting full data on a given year with no full one
    test.full_data = True
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 1
    assert oldies[0].pk == dls.pk

    ## Same tests with an existing load without year info
    # Ingesting full data on a given year with a wider existing full one.
    dls.full_data = True
    dls.year = None
    dls.save()
    valid, oldies = validate_data_load_source(test)
    assert not valid
    assert len(oldies) == 0

    # Ingesting additional data on a given year with an existing full one
    test.full_data = False
    valid, oldies = validate_data_load_source(test)
    assert not valid
    assert len(oldies) == 0

    # Ingesting additional data on a given year with no full one
    dls.full_data = False
    dls.save()
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    # Ingesting full data on a given year with no full one
    test.full_data = True
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    ## Same tests with the test data having no year info
    # Ingesting full data with a similar existing one.
    dls.full_data = True
    dls.year = None
    dls.save()
    test.full_data = True
    test.year = None

    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 1
    assert oldies[0].pk == dls.pk

    # Ingesting additional data on a given year with an existing full one
    test.full_data = False
    valid, oldies = validate_data_load_source(test)
    assert not valid
    assert len(oldies) == 0

    # Ingesting additional data on a given year with no full one
    dls.full_data = False
    dls.save()
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0

    # Ingesting full data on a given year with no full one
    test.full_data = True
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 1
    assert oldies[0].pk == dls.pk

    ## Test with adding a year to the existing one
    dls.full_data = True
    dls.year = 2020
    dls.save()
    test.year = None
    test.full_data = True

    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 1
    assert oldies[0].pk == dls.pk

    test.full_data = False
    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0


@pytest.mark.django_db
def test_multiple_dataset_replacement(datasources):
    print("Test loading fresh dataset to erase several existing ones.")
    dls_1 = DataLoadSourceFactory.create(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
        year=2020,
    )
    dls_2 = DataLoadSourceFactory.create(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
        year=2021,
    )
    dls_3 = DataLoadSourceFactory.create(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=False,
        year=2022,
    )
    test = dc.DataLoadSource(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )

    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 3
    for old in oldies:
        assert old.pk in [dls_1.pk, dls_2.pk, dls_3.pk]


@pytest.mark.django_db
def test_distinct_sources(datasources):
    print("Test loading fresh dataset to erase several existing ones.")
    dls_1 = DataLoadSourceFactory.create(
        data_source_id="pci",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    dls_2 = DataLoadSourceFactory.create(
        data_source_id="scipost",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )
    test = dc.DataLoadSource(
        data_source_id="operas",
        data_load_name="test_load",
        date_data_obtained=datetime.date.today(),
        full_data=True,
    )

    valid, oldies = validate_data_load_source(test)
    assert valid
    assert len(oldies) == 0
