import uuid

from django.db import models

from .currency import Currency
from .date import DateField
from .entity import Entity
from .source import DataLoadSource
from .utils import MATCH_SOURCE_CHOICES, TimestampedModel

# WARNING: those must be the names of the foreign keys in the Transfert model
TRANSFERT_ENTITY_TYPE_EMITTER = "emitter"
TRANSFERT_ENTITY_TYPE_RECIPIENT = "recipient"
TRANSFERT_ENTITY_TYPE_AGENT = "agent"
TRANSFERT_ENTITY_TYPE_CHOICES = {
    TRANSFERT_ENTITY_TYPE_EMITTER: "Emitter",
    TRANSFERT_ENTITY_TYPE_RECIPIENT: "Recipient",
    TRANSFERT_ENTITY_TYPE_AGENT: "Agent (group/consortium)",
}
TRANSFERT_ENTITY_TYPES = [
    TRANSFERT_ENTITY_TYPE_EMITTER,
    TRANSFERT_ENTITY_TYPE_RECIPIENT,
    TRANSFERT_ENTITY_TYPE_AGENT,
]

MATCH_CRITERIA_AUTO_MATCHED = "auto_match"
MATCH_CRITERIA_NEW_ENTITY = "new_entity"
MATCH_CRITERIA_CHILD = "is_child"
MATCH_CRITERIA_SAME_NAME_ONLY = "same_name_only"
MATCH_CRITERIA_SAME_NAME_COUNTRY = "same_name_country"
MATCH_CRITERIA_SAME_NAME_URL = "same_name_url"
MATCH_CRITERIA_SAME_PID = "same_pid"
MATCH_CRITERIA_MERGED = "merged"

TRANSFERT_ENTITY_MATCH_CRITERIA_CHOICES = {
    MATCH_CRITERIA_AUTO_MATCHED: "The entity was automatically matched.",
    MATCH_CRITERIA_NEW_ENTITY: "The entity was created for this transfert.",
    MATCH_CRITERIA_SAME_PID: "The entity has the same PID as the referenced one.",
    MATCH_CRITERIA_MERGED: "The previous entity the transfert was referring to was merged to this one.",
    MATCH_CRITERIA_CHILD: "The entity is a child of the referenced one.",
    MATCH_CRITERIA_SAME_NAME_ONLY: "The entity has the same name as the referenced one.",
    MATCH_CRITERIA_SAME_NAME_COUNTRY: "The entity has the same name and country as the referenced one",
    MATCH_CRITERIA_SAME_NAME_URL: "The entity has the same name and url as the referenced one.",
}


class Transfert(TimestampedModel):
    """
    Represents a money transfert between entities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    raw_data = models.JSONField()
    data_load_source = models.ForeignKey(
        DataLoadSource, null=False, on_delete=models.RESTRICT
    )
    emitter = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        related_name="transfert_as_emitters",
        related_query_name="transfert_as_emitter",
    )
    recipient = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        related_name="transfert_as_recipients",
        related_query_name="transfert_as_recipient",
    )
    agent = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        null=True,
        related_name="transfert_as_agents",
        related_query_name="transfert_as_agent",
    )
    amount = models.FloatField(null=True)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT, null=True)
    date_clc = DateField(null=True)
    date_invoice = DateField(null=True)
    date_payment = DateField(null=True)
    date_start = DateField(null=True)
    date_end = DateField(null=True)
    description = models.TextField()
    original_id = models.CharField(max_length=256)
    amounts_clc = models.JSONField(null=True)
    hide_amount = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_invoice__isnull=False)
                | models.Q(date_payment__isnull=False)
                | models.Q(date_start__isnull=False),
                name="transfert_at_least_one_date",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(date_start__isnull=True)
                    & models.Q(date_end__isnull=True)
                )
                | (
                    models.Q(date_start__isnull=False)
                    & models.Q(date_end__isnull=False)
                ),
                name="transfert_date_start_and_date_end_consistency",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(amount__isnull=False)
                    & models.Q(currency_id__isnull=False)
                )
                | (
                    models.Q(amount__isnull=True)
                    & models.Q(currency_id__isnull=True)
                ),
                name="transfert_amount_currency_consistency",
            ),
        ]


class TransfertEntityMatching(TimestampedModel):
    """
    Logs how each entity was matched to a transfert.
    """

    id = models.BigAutoField(primary_key=True)
    transfert = models.ForeignKey(Transfert, on_delete=models.CASCADE)
    transfert_entity_type = models.CharField(
        choices=TRANSFERT_ENTITY_TYPE_CHOICES, max_length=32
    )
    entity = models.ForeignKey(Entity, on_delete=models.RESTRICT)
    match_criteria = models.CharField(
        choices=TRANSFERT_ENTITY_MATCH_CRITERIA_CHOICES, max_length=32
    )
    match_source = models.CharField(choices=MATCH_SOURCE_CHOICES, max_length=32)
    comments = models.TextField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    transfert_entity_type__in=list(
                        TRANSFERT_ENTITY_TYPE_CHOICES.keys()
                    )
                ),
                name="valid_transfert_entity_type_choices",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_criteria__in=list(
                        TRANSFERT_ENTITY_MATCH_CRITERIA_CHOICES.keys()
                    )
                ),
                name="transfert_entity_valid_match_criteria_choices",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_source__in=list(MATCH_SOURCE_CHOICES.keys())
                ),
                name="transfert_entity_valid_match_source_choices",
            ),
        ]
