from django.db import models

from .utils import TimestampedModel


class Registry(TimestampedModel):
    """
    Represents a registry of Permanent Identifier (PIDs).
    Ex: ROR, Wikidata, ...
    """

    id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=128)
    website = models.URLField(max_length=256)
    link_template = models.CharField(max_length=256)
    record_regex = models.CharField(max_length=128, null=True)
