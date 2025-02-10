from __future__ import annotations

import uuid

from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from .utils import TimestampedModel


def entity_logo_path(instance: Entity, filename: str) -> str:
    """Return the file path where to store the entity logo file"""
    return f"{instance.id}/{filename}"


class Entity(TimestampedModel):
    """
    Represents an entity involved in a transfert.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    raw_name = models.CharField(max_length=512)
    raw_country = models.CharField(
        max_length=2,
        null=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
    )
    raw_website = models.URLField(max_length=256, null=True)

    is_active = models.BooleanField(default=True)
    is_matchable = models.BooleanField(default=True)
    merged_with = models.ForeignKey(
        "self", on_delete=models.RESTRICT, null=True
    )
    merged_criteria = models.CharField(max_length=512, null=True)

    ## CLC fields filled from raw data and PID records.
    name = models.CharField(max_length=512)
    country = models.CharField(
        max_length=2,
        null=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
    )
    website = models.URLField(max_length=256, null=True)
    logo_url = models.CharField(max_length=256, null=True)
    logo = models.ImageField(
        upload_to=entity_logo_path, max_length=256, null=True
    )
    date_logo_fetched = models.DateTimeField(null=True)
    wikipedia_url = models.CharField(max_length=512, null=True)
    wikipedia_extract = models.TextField(null=True)
    date_wikipedia_fetched = models.DateTimeField(null=True)
    # Coordinates according to WGS84 coordinates system in form `POINT(LAT LNG)`
    coordinates = models.TextField(null=True)

    ##  Clc booleans indicating if the entity is involved in 1+ transfert
    #   as an emitter, recipient, agent
    is_emitter = models.BooleanField(default=False)
    is_recipient = models.BooleanField(default=False)
    is_agent = models.BooleanField(default=False)

    # Infrastructures characterization
    infra_finder_url = models.URLField(max_length=256, null=True)
    posi_url = models.URLField(max_length=256, null=True)
    is_scoss_awarded = models.BooleanField(default=False)
    is_partner = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(merged_with_id__isnull=True)
                    & models.Q(merged_criteria__isnull=True)
                )
                | (
                    models.Q(merged_with_id__isnull=False)
                    & models.Q(merged_criteria__isnull=False)
                ),
                name="entity_merged_with_merged_criteria_consistency",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(merged_with_id__isnull=True)
                    | ~models.Q(merged_with_id=models.F("id"))
                ),
                name="entity_not_merged_with_self",
            ),
        ]


class EntityType(TimestampedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128)
