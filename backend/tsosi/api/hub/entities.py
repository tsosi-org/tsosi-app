"""
The organization's page preview and supports table.
"""

from django.db.models import Prefetch, QuerySet
from rest_framework import serializers
from rest_framework.response import Response

from tsosi.api.hub.base import (
    HubView,
    IsMemberOrStaff,
    get_hub_entity,
    hub_entities,
)
from tsosi.api.serializers import EntityDetailsSerializer, is_amount_hidden
from tsosi.models import DataLoadSource, Entity, Transfer
from tsosi.models.entity import (
    ENTITY_SCOPE_IN,
    ENTITY_SCOPE_OUT,
    ENTITY_SCOPE_TO_CHECK,
)

# Statuses of a transfer in the organization's supports table
SUPPORT_STATUS_CONFIRMED = "confirmed"
SUPPORT_STATUS_NOT_CONFIRMED = "not_confirmed"


def table_supports(entity: Entity) -> QuerySet:
    """
    The supports of the organization's table that it can change: those it's
    part of, not those of its children.
    """
    return Transfer.objects.filter_by_entity(
        entity, include_children=False
    ).filter(merged_into__isnull=True)


def preview_reason(entity: Entity) -> str | None:
    """
    Why the entity is not on the public site, or None if it is.
    """
    if Entity.objects.public().filter(id=entity.id).exists():
        return None
    if entity.scope in [ENTITY_SCOPE_TO_CHECK, ENTITY_SCOPE_OUT]:
        return entity.scope
    return "no_public_support"


def with_table_values(transfers: QuerySet) -> QuerySet:
    """
    The transfers with the relations that `HubTransferSerializer` reads,
    latest first.
    """
    return (
        transfers.select_related("emitter", "recipient")
        .prefetch_related(
            "agents",
            Prefetch(
                "data_load_sources",
                queryset=DataLoadSource.objects.select_related("entity"),
            ),
        )
        .order_by("-date_clc", "id")
    )


def transfers_entity_ids(transfers) -> set:
    """The IDs of the emitters, recipients and agents of the transfers."""
    entity_ids = set()
    for transfer in transfers:
        entity_ids |= {transfer.emitter_id, transfer.recipient_id}
        entity_ids |= {a.id for a in transfer.agents.all()}
    return entity_ids


class HubTransferSerializer(serializers.ModelSerializer):
    """
    A transfer of the organization's supports table: amounts are always
    shown, with whether they're hidden on the public site, and the
    organizations that declared it.
    The organization is passed as `entity` in the context.
    """

    agent_ids = serializers.PrimaryKeyRelatedField(
        source="agents", many=True, read_only=True
    )
    currency = serializers.ReadOnlyField(source="currency_id")
    amount_hidden = serializers.SerializerMethodField()
    declared_by = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_public = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            "id",
            "emitter_id",
            "recipient_id",
            "agent_ids",
            "amount",
            "currency",
            "amounts_clc",
            "date_clc",
            "date_invoice",
            "date_payment_emitter",
            "date_payment_recipient",
            "date_start",
            "date_end",
            "description",
            "amount_hidden",
            "declared_by",
            "status",
            "is_public",
        ]

    def get_amount_hidden(self, obj: Transfer) -> bool:
        return obj.amount is not None and is_amount_hidden(obj)

    def get_declared_by(self, obj: Transfer) -> list[dict]:
        """
        The organizations that declared the transfer, with the latest date
        their data was obtained. The data load sources of a merged transfer
        are those of all its source transfers.
        """
        declarations = {}
        for source in obj.data_load_sources.all():
            key = source.entity_id or source.data_source_id
            previous = declarations.get(key)
            if previous and previous["date"] >= source.date_data_obtained:
                continue
            declarations[key] = {
                "id": source.entity_id,
                "name": (
                    source.entity.name
                    if source.entity
                    else source.data_source_id
                ),
                "short_name": source.entity and source.entity.short_name,
                "date": source.date_data_obtained,
            }
        return sorted(declarations.values(), key=lambda d: d["date"])

    def get_is_public(self, obj: Transfer) -> bool:
        """Whether it's on the public site, with its page."""
        return (
            obj.merged_into_id is None
            and obj.recipient.scope == ENTITY_SCOPE_IN
            and not obj.is_future
        )

    def get_status(self, obj: Transfer) -> str:
        entity = self.context["entity"]
        if any(s.entity_id == entity.id for s in obj.data_load_sources.all()):
            return SUPPORT_STATUS_CONFIRMED
        return SUPPORT_STATUS_NOT_CONFIRMED


class EntityPreviewView(HubView):
    """
    GET: the details of an entity, public or not, for the users who can edit
    it: the page's preview when the entity is not on the public site yet.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)
        data = EntityDetailsSerializer(
            entity, context={"request": request}
        ).data
        return Response({**data, "preview_reason": preview_reason(entity)})


class EntityTransfersView(HubView):
    """
    GET: the organization's supports table, for its members and the TSOSI
    team. Unlike the public API, it lists the transfers of all scopes, future
    ones included, with their amounts. Not those of its children: each
    organization manages its own supports in its Hub.
    `entities` holds the transfers' entities missing from the frontend's
    reference data (see `hub_entities`).
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)
        transfers = with_table_values(table_supports(entity))
        entity_ids = {entity.id} | transfers_entity_ids(transfers)
        return Response(
            {
                "transfers": HubTransferSerializer(
                    transfers, many=True, context={"entity": entity}
                ).data,
                "entities": hub_entities(request, entity_ids),
            }
        )
