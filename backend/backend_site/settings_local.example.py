DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "YOUR_HOST",
        "USER": "YOUR_POSTGRESQL_USER",
        "NAME": "YOUR_POSTGRESQL_DATABASE",
        "PASSWORD": "YOUR_PASSWORD",
        "PORT": 5432,  # Default port
    }
}

SECRET_KEY = "MY_SECRET_KEY"
DEBUG = True
MEDIA_ROOT = "/var/tsosi_media/"
MEDIA_URL = "media/"
TSOSI_MAIN_LOG_FILE = "/var/log/tsosi/tsosi_app.log"
TSOSI_DATA_LOG_FILE = "/var/log/tsosi/tsosi_data.log"
TSOSI_DJANGO_LOG_FILE = "/var/log/tsosi/django.log"
DJANGO_LOG_LEVEL = "INFO"
TSOSI_REDIS_HOST = "127.0.0.1"
TSOSI_REDIS_PORT = "6379"
TSOSI_REDIS_DB = "0"
TSOSI_CELERY_BROKER_URL = (
    f"redis://{TSOSI_REDIS_HOST}:{TSOSI_REDIS_PORT}/{TSOSI_REDIS_DB}"
)
