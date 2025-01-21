from django.db import models
from django.utils import timezone

MATCH_SOURCE_MANUAL = "manual"
MATCH_SOURCE_AUTOMATIC = "automatic"
MATCH_SOURCE_CHOICES = {
    MATCH_SOURCE_MANUAL: "manual",
    MATCH_SOURCE_AUTOMATIC: "automatic",
}


class TimestampedModel(models.Model):
    date_created = models.DateTimeField(default=timezone.now)
    date_last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
