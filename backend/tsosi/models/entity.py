from __future__ import annotations

import uuid

from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from .api_request import ApiRequest
from .utils import TimestampedModel


def entity_logo_path(instance: Entity, filename: str) -> str:
    """Return the file path where to store the entity logo file"""
    return f"{instance.id}/logo/{filename}"


def entity_icon_path(instance: Entity, filename: str) -> str:
    """Return the file path where to store the entity icon file"""
    return f"{instance.id}/icon/{filename}"


class Entity(TimestampedModel):
    """
    Represents an entity involved in a transfer.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    raw_name = models.CharField(max_length=512)
    raw_country = models.CharField(
        max_length=2,
        null=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
    )
    raw_website = models.URLField(max_length=256, null=True)
    # Description text taking is prioritized over the Wikipedia extract.
    # It corresponds to a manual input, only for the infrastructures for now.
    description = models.TextField(null=True)
    # This overrides the default behavior of fetching the logo from wikimedia.
    # To be verified.
    manual_logo = models.BooleanField(default=False)
    # Short name for an entity.
    short_name = models.CharField(max_length=128, null=True)

    is_active = models.BooleanField(default=True)
    is_matchable = models.BooleanField(default=True)
    merged_with = models.ForeignKey(
        "self", on_delete=models.RESTRICT, null=True
    )
    merged_criteria = models.CharField(max_length=512, null=True)
    icon = models.ImageField(
        upload_to=entity_icon_path, max_length=256, null=True
    )

    ## CLC fields filled from raw data and PID records.
    name = models.CharField(max_length=512)
    country = models.CharField(
        max_length=2,
        null=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
    )
    website = models.URLField(max_length=256, null=True)
    date_inception = models.DateField(null=True)

    logo_url = models.CharField(max_length=256, null=True)
    logo = models.ImageField(
        upload_to=entity_logo_path, max_length=256, null=True
    )
    date_logo_fetched = models.DateTimeField(null=True)

    wikipedia_url = models.CharField(max_length=512, null=True)
    wikipedia_extract = models.TextField(null=True)
    date_wikipedia_fetched = models.DateTimeField(null=True)

    is_partner = models.BooleanField(default=False)
    # Coordinates according to WGS84 coordinates system in form `POINT(LNG LAT)`
    # TODO: Use two distinct fields, `lon` & `lat` for coordinates as we will
    # never use something else than point coordinates.
    coordinates = models.TextField(null=True)

    ##  Clc booleans indicating if the entity is involved in 1+ transfer
    #   as an emitter, recipient, agent
    is_emitter = models.BooleanField(default=False)
    is_recipient = models.BooleanField(default=False)
    is_agent = models.BooleanField(default=False)

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


class InfrastructureDetails(TimestampedModel):
    entity = models.OneToOneField(
        Entity, on_delete=models.CASCADE, related_name="infrastructure_details"
    )
    infra_finder_url = models.URLField(max_length=256, null=True)
    posi_url = models.URLField(max_length=256, null=True)
    support_url = models.URLField(max_length=256, null=True)

    date_scoss_start = models.DateField(null=True)
    date_scoss_end = models.DateField(null=True)

    legal_entity_description = models.TextField(null=True)

    hide_amount = models.BooleanField(default=False)
    # Clc fields
    date_data_update = models.DateField(null=True)
    date_data_start = models.DateField(null=True)
    date_data_end = models.DateField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(date_scoss_start__isnull=True)
                    & models.Q(date_scoss_end__isnull=True)
                )
                | (
                    models.Q(date_scoss_start__isnull=False)
                    & models.Q(date_scoss_end__isnull=False)
                ),
                name="infrastructure_details_scoss_dates_coherency_1",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(date_scoss_start__isnull=True)
                    & models.Q(date_scoss_end__isnull=True)
                )
                | (models.Q(date_scoss_start__lte=models.F("date_scoss_end"))),
                name="infrastructure_details_scoss_dates_coherency_2",
            ),
        ]


class EntityType(TimestampedModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128)


ENTITY_REQUEST_WIKIPEDIA_EXTRACT = "wikipedia_extract"
ENTITY_REQUEST_WIKIMEDIA_LOGO = "wikimedia_logo"
ENTITY_REQUEST_CHOICES = {
    ENTITY_REQUEST_WIKIPEDIA_EXTRACT: "Wikipedia extract",
    ENTITY_REQUEST_WIKIMEDIA_LOGO: "Wikimedia logo",
}


class EntityRequest(ApiRequest):
    """
    Model to log every external API requests made to enrich the entity
    model.
    """

    entity = models.ForeignKey(
        Entity, null=False, on_delete=models.CASCADE, related_name="requests"
    )
    type = models.CharField(
        choices=ENTITY_REQUEST_CHOICES, null=False, max_length=32
    )

    class Meta(ApiRequest.Meta):
        constraints = [*ApiRequest.Meta.constraints]
        constraints.append(
            models.CheckConstraint(
                condition=models.Q(
                    type__in=list(ENTITY_REQUEST_CHOICES.keys())
                ),
                name="valid_entity_request_type_choice",
            )
        )
