"""
Settings file to be used on production server.
This file is just an example and is never used.
TODO: Replace all `{REPLACE}` place holders with actual values/secrets.
"""

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "{REPLACE}",
        "USER": "{REPLACE}",
        "NAME": "{REPLACE}",
        "PASSWORD": "{REPLACE}",
        "PORT": 5432,
    }
}

SECRET_KEY = "{REPLACE}"
DEBUG = False
# This needs to be sync with nginx config, usually /tsosi_media
MEDIA_ROOT = "{REPLACE}"
MEDIA_URL = "media/"
STATIC_URL = "static/"
ALLOWED_HOSTS = [
    "tsosi.org",
    "www.tsosi.org",
    "tsosi.u-ga.fr",
    "127.0.0.1",
    # External IP
    "129.88.178.178",
]
# Log config
TSOSI_MAIN_LOG_FILE = "/var/log/tsosi_app.log"
TSOSI_DATA_LOG_FILE = "/var/log/tsosi_data.log"
TSOSI_DJANGO_LOG_FILE = "/var/log/django.log"
TSOSI_ERROR_OUTPUT_FOLDER = "/var/log/tsosi_errors"
DJANGO_LOG_LEVEL = "INFO"
TSOSI_LOG_LEVEL = "INFO"
ERROR_LOG_FILE = "/var/log/error.log"
# Redis config
TSOSI_REDIS_HOST = "127.0.0.1"
TSOSI_REDIS_PORT = 6379
TSOSI_REDIS_DB = 0
TSOSI_CELERY_BROKER_URL = (
    f"redis://{TSOSI_REDIS_HOST}:{TSOSI_REDIS_PORT}/{TSOSI_REDIS_DB}"
)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{TSOSI_REDIS_HOST}:{TSOSI_REDIS_PORT}/{TSOSI_REDIS_DB}",
    }
}
# Job related settings
TSOSI_TO_INGEST_DIR = "{REPLACE}"
TSOSI_TRIGGER_JOBS = True
# API related
# TODO: Add UGA network IPV4 prefixes
TSOSI_API_WHITELIST_IPS = ["127.0.0.1"]
DRF_NUM_PROXIES = 1
TSOSI_FRONTEND_CUSTOM_HEADER = "X-Frontend-Origin"
TSOSI_PUBLIC_RELPATH = "../public/"
