import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
NO_GIT_DIR = BACKEND_DIR / "_no_git"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "db",
        "USER": "tsosi_user",
        "NAME": "tsosi_db",
        "PASSWORD": "tsosi_password",
        "PORT": 5432,
    }
}

SECRET_KEY = "MY_SECRET_KEY"
DEBUG = True
MEDIA_ROOT = f"{NO_GIT_DIR}/media/"
MEDIA_URL = "media/"
STATIC_URL = "static/"
ALLOWED_HOSTS = ["127.0.0.1", "172.17.0.1", "localhost"]
TSOSI_MAIN_LOG_FILE = f"{NO_GIT_DIR}/logs/tsosi_app.log"
TSOSI_DATA_LOG_FILE = f"{NO_GIT_DIR}/logs/tsosi_data.log"
TSOSI_DJANGO_LOG_FILE = f"{NO_GIT_DIR}/logs/django.log"
DJANGO_LOG_LEVEL = "INFO"
TSOSI_LOG_LEVEL = "INFO"
ERROR_LOG_FILE = f"{NO_GIT_DIR}/logs/error.log"
TSOSI_REDIS_HOST = "redis"
TSOSI_REDIS_PORT = "6379"
TSOSI_REDIS_DB = "0"
TSOSI_CELERY_BROKER_URL = (
    f"redis://{TSOSI_REDIS_HOST}:{TSOSI_REDIS_PORT}/{TSOSI_REDIS_DB}"
)
TSOSI_DATA_EXPORT_FOLDER = ""
TSOSI_TO_INGEST_DIR = TSOSI_DATA_EXPORT_FOLDER
TSOSI_TRIGGER_JOBS = True
TSOSI_SCIPOST_AUTH = {
    "username": "",
    "password": "",
    "client_id": "",
    "client_secret": "",
}

if "test" in sys.argv or "pytest" in sys.modules:
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3"}
