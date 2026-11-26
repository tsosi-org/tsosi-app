"""
Monitoring of the app.
"""

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

CELERY_HEARTBEAT_CACHE_KEY = "tsosi_celery_heartbeat"

CELERY_HEARTBEAT_MAX_AGE = 30 * 60
HEARTBEAT_TIMEOUT = 10


def read_release(public_dir: Path) -> str | None:
    """
    The deployed commit, so that the
    backend and frontend errors share the same release.
    """
    try:
        with open(public_dir / "deployment.json") as f:
            commit_hash = json.load(f).get("hash")
    except (OSError, ValueError):
        return None
    return commit_hash[:12] if commit_hash else None


def init_error_tracking(
    dsn: str | None,
    environment: str,
    release: str | None,
    traces_sample_rate: float = 0.0,
) -> bool:
    """
    Initialize the Sentry SDK, if a DSN is set. Returns whether it was.
    """
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=False,
        traces_sample_rate=traces_sample_rate,
        auto_session_tracking=False,
        integrations=[DjangoIntegration(), CeleryIntegration()],
    )
    return True


def ping_heartbeat(url: str) -> None:
    """
    Signal a run to a GlitchTip heartbeat monitor.
    """
    try:
        requests.post(url, timeout=HEARTBEAT_TIMEOUT)
    except requests.RequestException as e:
        logger.warning(f"Heartbeat ping failed: {e}")


def record_celery_heartbeat() -> None:
    from django.core.cache import cache

    cache.set(CELERY_HEARTBEAT_CACHE_KEY, time.time(), timeout=None)


def health_checks() -> dict[str, bool]:
    """
    The state of the services the app needs.
    """
    from django.core.cache import cache
    from django.db import connection

    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        logger.exception("Health check: database unreachable")
        checks["database"] = False

    try:
        cache.set("tsosi_health_check", 1, timeout=60)
        checks["cache"] = cache.get("tsosi_health_check") == 1
        last_heartbeat = cache.get(CELERY_HEARTBEAT_CACHE_KEY)
    except Exception:
        logger.exception("Health check: cache unreachable")
        checks["cache"] = False
        last_heartbeat = None

    checks["celery"] = (
        last_heartbeat is not None
        and time.time() - last_heartbeat < CELERY_HEARTBEAT_MAX_AGE
    )
    return checks
