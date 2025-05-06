"""
File declaring global fixtures for all tests.
"""

import pytest
from tsosi.models.source import DataLoadSource, DataSource
from tsosi.models.static_data import create_pid_registries, create_sources


@pytest.fixture
def registries(db):
    create_pid_registries()


@pytest.fixture
def datasources(db):
    create_sources()


@pytest.fixture
def storage(settings):
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage"
            # "BACKEND": "django.core.files.storage.FileSystemStorage",
            # # "OPTIONS": {
            # #     "location": "/tsosi_test_media",
            # #     "base_url": "/example/",
            # # },
        }
    }
