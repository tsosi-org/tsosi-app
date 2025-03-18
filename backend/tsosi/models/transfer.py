import uuid

from django.db import models

from .currency import Currency
from .date import DateField
from .entity import Entity
from .source import DataLoadSource
from .utils import MATCH_SOURCE_CHOICES, TimestampedModel

# WARNING: those must be the names of the foreign keys in the Transfer model
TRANSFER_ENTITY_TYPE_EMITTER = "emitter"
TRANSFER_ENTITY_TYPE_RECIPIENT = "recipient"
TRANSFER_ENTITY_TYPE_AGENT = "agent"
TRANSFER_ENTITY_TYPE_CHOICES = {
    TRANSFER_ENTITY_TYPE_EMITTER: "Emitter",
    TRANSFER_ENTITY_TYPE_RECIPIENT: "Recipient",
    TRANSFER_ENTITY_TYPE_AGENT: "Intermediary (group/consortium)",
}
TRANSFER_ENTITY_TYPES = [
    TRANSFER_ENTITY_TYPE_EMITTER,
    TRANSFER_ENTITY_TYPE_RECIPIENT,
    TRANSFER_ENTITY_TYPE_AGENT,
]

MATCH_CRITERIA_AUTO_MATCHED = "auto_match"
MATCH_CRITERIA_NEW_ENTITY = "new_entity"
MATCH_CRITERIA_CHILD = "is_child"
MATCH_CRITERIA_SAME_NAME_ONLY = "same_name_only"
MATCH_CRITERIA_SAME_NAME_COUNTRY = "same_name_country"
MATCH_CRITERIA_SAME_NAME_URL = "same_name_url"
MATCH_CRITERIA_SAME_PID = "same_pid"
MATCH_CRITERIA_MERGED = "merged"

TRANSFER_ENTITY_MATCH_CRITERIA_CHOICES = {
    MATCH_CRITERIA_AUTO_MATCHED: "The entity was automatically matched.",
    MATCH_CRITERIA_NEW_ENTITY: "The entity was created for this transfer.",
    MATCH_CRITERIA_SAME_PID: "The entity has the same PID as the referenced one.",
    MATCH_CRITERIA_MERGED: "The previous entity the transfer was referring to was merged to this one.",
    MATCH_CRITERIA_CHILD: "The entity is a child of the referenced one.",
    MATCH_CRITERIA_SAME_NAME_ONLY: "The entity has the same name as the referenced one.",
    MATCH_CRITERIA_SAME_NAME_COUNTRY: "The entity has the same name and country as the referenced one",
    MATCH_CRITERIA_SAME_NAME_URL: "The entity has the same name and url as the referenced one.",
}


class Transfer(TimestampedModel):
    """
    Represents a money transfer between entities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    raw_data = models.JSONField()
    data_load_source = models.ForeignKey(
        DataLoadSource, null=False, on_delete=models.RESTRICT
    )
    emitter = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        related_name="transfer_as_emitters",
        related_query_name="transfer_as_emitter",
    )
    recipient = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        related_name="transfer_as_recipients",
        related_query_name="transfer_as_recipient",
    )
    agent = models.ForeignKey(
        Entity,
        on_delete=models.RESTRICT,
        null=True,
        related_name="transfer_as_agents",
        related_query_name="transfer_as_agent",
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
    original_amount_field = models.CharField(max_length=128)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_invoice__isnull=False)
                | models.Q(date_payment__isnull=False)
                | models.Q(date_start__isnull=False),
                name="transfer_at_least_one_date",
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
                name="transfer_date_start_and_date_end_consistency",
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
                name="transfer_amount_currency_consistency",
            ),
        ]


class TransferEntityMatching(TimestampedModel):
    """
    Logs how each entity was matched to a transfer.
    """

    id = models.BigAutoField(primary_key=True)
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    transfer_entity_type = models.CharField(
        choices=TRANSFER_ENTITY_TYPE_CHOICES, max_length=32
    )
    entity = models.ForeignKey(Entity, on_delete=models.RESTRICT)
    match_criteria = models.CharField(
        choices=TRANSFER_ENTITY_MATCH_CRITERIA_CHOICES, max_length=32
    )
    match_source = models.CharField(choices=MATCH_SOURCE_CHOICES, max_length=32)
    comments = models.TextField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    transfer_entity_type__in=list(
                        TRANSFER_ENTITY_TYPE_CHOICES.keys()
                    )
                ),
                name="valid_transfer_entity_type_choices",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_criteria__in=list(
                        TRANSFER_ENTITY_MATCH_CRITERIA_CHOICES.keys()
                    )
                ),
                name="transfer_entity_valid_match_criteria_choices",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    match_source__in=list(MATCH_SOURCE_CHOICES.keys())
                ),
                name="transfer_entity_valid_match_source_choices",
            ),
        ]
