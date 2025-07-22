"""
File declaring global fixtures for all tests.
"""

import json
from pathlib import Path

import pytest
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


@pytest.fixture
def uga_ror_record() -> dict:
    fixture_path = (
        Path(__file__).resolve().parent / "fixtures/ror_02rx3b187.json"
    )
    with open(fixture_path, "r") as f:
        file_content = json.load(f)
    return file_content


@pytest.fixture
def uga_wikipedia_summary() -> dict:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures/wikipedia_summary_grenoble_alpes_university.json"
    )
    with open(fixture_path, "r") as f:
        file_content = json.load(f)
    return file_content


@pytest.fixture
def uga_logo() -> bytes:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures/Logo_Université_Grenoble-Alpes_(2020).jpg"
    )
    with open(fixture_path, "rb") as f:
        file_content = f.read()
    return file_content
