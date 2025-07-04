from django.db import models
from django.utils import timezone

from .api_request import ApiRequest
from .entity import Entity
from .registry import Registry
from .utils import MATCH_SOURCE_CHOICES, TimestampedModel

MATCH_CRITERIA_FROM_INPUT = "from_input"
MATCH_CRITERIA_EXACT_MATCH = "exact_match"
MATCH_CRITERIA_FROM_ROR = "from_ror"
MATCH_CRITERIA_FROM_WIKIDATA = "from_wikidata"

IDENTIFIER_ENTITY_MATCH_CRITERIA_CHOICES = {
    MATCH_CRITERIA_FROM_INPUT: "The PID was given in the input data.",
    MATCH_CRITERIA_EXACT_MATCH: "The PID associated name matches exactly to the entity name.",
    MATCH_CRITERIA_FROM_ROR: "The PID was fetched from the entity's ROR record.",
    MATCH_CRITERIA_FROM_WIKIDATA: "The PID was fetched from the entity's Wikidata record.",
}


class Identifier(TimestampedModel):
    """
    Represents an external Permanent Identifier (PID).
    """

    id = models.BigAutoField(primary_key=True)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    entity = models.ForeignKey(
        Entity, related_name="identifiers", on_delete=models.SET_NULL, null=True
    )
    current_version = models.ForeignKey(
        "IdentifierVersion",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_under_review = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["registry", "value"], name="unique_value_per_registry"
            ),
            models.UniqueConstraint(
                fields=["registry", "entity"],
                name="unique_identifier_per_registry_and_entity",
            ),
        ]


class IdentifierVersion(TimestampedModel):
    """
    Holds the data of a version of a Permanent Identifier (PID).
    """

    id = models.BigAutoField(primary_key=True)
    identifier = models.ForeignKey(Identifier, on_delete=models.CASCADE)
    value = models.JSONField()
    date_start = models.DateTimeField(default=timezone.now)
    # null date_end corresponds to current version
    date_end = models.DateTimeField(null=True)
    date_last_fetched = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identifier"],
                condition=models.Q(date_end__isnull=True),
                name="unique_identifier_version_with_no_date_end",
            ),
        ]


class IdentifierEntityMatching(TimestampedModel):
    """
    Logs how each identifier was matched to an entity.
    """

    id = models.BigAutoField(primary_key=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    identifier = models.ForeignKey(Identifier, on_delete=models.CASCADE)
    match_criteria = models.CharField(
        choices=IDENTIFIER_ENTITY_MATCH_CRITERIA_CHOICES, max_length=32
    )
    match_source = models.CharField(choices=MATCH_SOURCE_CHOICES, max_length=32)
    date_start = models.DateTimeField(default=timezone.now)
    # If the date is null, that means the matching is active.
    date_end = models.DateTimeField(null=True)
    comments = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identifier"],
                condition=models.Q(date_end__isnull=True),
                name="unique_identifier_with_no_date_end",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_criteria__in=list(
                        IDENTIFIER_ENTITY_MATCH_CRITERIA_CHOICES.keys()
                    )
                ),
                name="identifier_entity_valid_match_criteria_choices",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_source__in=list(MATCH_SOURCE_CHOICES.keys())
                ),
                name="identifier_entity_valid_match_source_choices",
            ),
        ]


class IdentifierRequest(ApiRequest):
    """
    Model to log every requests performed to fetch the identifier records.
    This is used to stop requesting the registry when the request keeps
    failing.
    """

    identifier = models.ForeignKey(
        Identifier,
        null=False,
        on_delete=models.CASCADE,
        related_name="requests",
    )
