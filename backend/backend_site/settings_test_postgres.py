"""
Settings to run the tests on PostgreSQL, as in production, instead of the
SQLite database that `settings_local.py` uses for the tests:

    poetry run pytest --ds=backend_site.settings_test_postgres

SQLite ignores `select_for_update` and stores JSON differently. Django
creates and drops its own test database (`test_<NAME>`) on the server given
by the `TSOSI_TEST_DB_*` environment variables, by default the DevContainer
`db` service. From the host: `TSOSI_TEST_DB_HOST=localhost
TSOSI_TEST_DB_PORT=5433`.
"""

import os

from backend_site.settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("TSOSI_TEST_DB_HOST", "db"),
        "PORT": int(os.environ.get("TSOSI_TEST_DB_PORT", 5432)),
        "USER": os.environ.get("TSOSI_TEST_DB_USER", "tsosi_user"),
        "PASSWORD": os.environ.get("TSOSI_TEST_DB_PASSWORD", "tsosi_password"),
        "NAME": os.environ.get("TSOSI_TEST_DB_NAME", "tsosi_db"),
    }
}
