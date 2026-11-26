import json
import time
from unittest import mock

import pytest
import requests
from django.core.cache import cache
from django.test import Client

from tsosi import monitoring, tasks


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_read_release(tmp_path):
    assert monitoring.read_release(tmp_path) is None
    (tmp_path / "deployment.json").write_text("not json")
    assert monitoring.read_release(tmp_path) is None
    (tmp_path / "deployment.json").write_text(
        json.dumps({"hash": "29324d1a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"})
    )
    assert monitoring.read_release(tmp_path) == "29324d1a0b1c"


def test_no_error_tracking_without_dsn():
    with mock.patch("sentry_sdk.init") as init:
        assert not monitoring.init_error_tracking(None, "production", None)
        assert not monitoring.init_error_tracking("", "production", None)
    init.assert_not_called()


def test_error_tracking_sends_no_personal_data():
    with mock.patch("sentry_sdk.init") as init:
        assert monitoring.init_error_tracking(
            "https://key@monitoring.example.org/1", "dev", "abc", 0.05
        )
    kwargs = init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["auto_session_tracking"] is False
    assert kwargs["environment"] == "dev"
    assert kwargs["release"] == "abc"


@pytest.mark.django_db
def test_health_ok():
    tasks.celery_heartbeat()
    response = Client().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": True, "cache": True, "celery": True},
    }


@pytest.mark.django_db
def test_health_without_celery_heartbeat():
    response = Client().get("/api/health")
    assert response.status_code == 503
    assert response.json()["checks"]["celery"] is False

    cache.set(
        monitoring.CELERY_HEARTBEAT_CACHE_KEY,
        time.time() - monitoring.CELERY_HEARTBEAT_MAX_AGE - 1,
    )
    assert Client().get("/api/health").status_code == 503


@pytest.mark.django_db
def test_health_database_down():
    tasks.celery_heartbeat()
    with mock.patch(
        "django.db.backends.utils.CursorWrapper.execute",
        side_effect=Exception("down"),
    ):
        response = Client().get("/api/health")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] is False


def test_heartbeat_pinged_after_task_success(settings):
    url = "https://monitoring.example.org/api/0/organizations/t/heartbeat_check/u/"
    settings.TSOSI_HEARTBEATS = {"tsosi.tasks.celery_heartbeat": url}
    with mock.patch("tsosi.monitoring.requests.post") as post:
        tasks.ping_task_heartbeat(sender=tasks.celery_heartbeat)
        tasks.ping_task_heartbeat(sender=tasks.refresh_news)
    post.assert_called_once_with(url, timeout=monitoring.HEARTBEAT_TIMEOUT)


def test_heartbeat_failure_doesnt_raise():
    with mock.patch(
        "tsosi.monitoring.requests.post",
        side_effect=requests.ConnectionError("unreachable"),
    ):
        monitoring.ping_heartbeat("https://monitoring.example.org/")
