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
TSOSI_MAIN_LOG_FILE = "/var/log/my_file.log"
TSOSI_DATA_LOG_FILE = "/var/log/my_data_file.log"
DJANGO_LOG_LEVEL = "INFO"
