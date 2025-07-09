import pytest
from tsosi.tasks import ingest_test


@pytest.mark.django_db
def test_ingest_test_data(registries):
    print("Testing test data ingestion")
    ingest_test()
