from django.apps import AppConfig


class TsosiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tsosi"

    def ready(self):
        from . import signals
