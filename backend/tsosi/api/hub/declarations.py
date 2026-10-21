"""
The organization's changes to its supports (declarations), saved as drafts
until submitted.
"""

import math
import re
from datetime import date

from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import Http404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from tsosi.api.hub.base import (
    HubView,
    IsMemberOrStaff,
    get_declaring_entity,
    get_hub_entity,
    hub_entities,
)
from tsosi.api.hub.entities import table_supports
from tsosi.data.hub_reconciliation import possible_duplicates
from tsosi.data.ingestion.transfer_matching import date_contains
from tsosi.models import Currency, Declaration, Entity, Transfer
from tsosi.models.date import (
    DATE_PRECISION_DAY,
    DATE_PRECISION_MONTH,
    DATE_PRECISION_YEAR,
    Date,
)
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
    DECLARATION_KINDS_RECONCILIATION,
    DECLARATION_KINDS_SUPPORT_CHANGES,
    DECLARATION_KINDS_WITH_VALUES,
    DECLARATION_STATUS_DRAFT,
)

DATE_INPUT_REGEX = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


class PrecisionDateField(serializers.Field):
    """
    A date with its precision, typed as `2024`, `2024-03` or `2024-03-13`,
    stored and returned as `{"value": "2024-03-01", "precision": "month"}`.
    """

    default_error_messages = {
        "invalid": "Enter a date as YYYY, YYYY-MM or YYYY-MM-DD."
    }

    def to_internal_value(self, data) -> dict:
        match = (
            DATE_INPUT_REGEX.match(data.strip())
            if isinstance(data, str)
            else None
        )
        if match is None:
            self.fail("invalid")
        year, month, day = match.groups()
        try:
            value = date(int(year), int(month or 1), int(day or 1))
        except ValueError:
            self.fail("invalid")
        precision = (
            DATE_PRECISION_DAY
            if day
            else DATE_PRECISION_MONTH if month else DATE_PRECISION_YEAR
        )
        return Date(value=value, precision=precision).serialize()

    def to_representation(self, value: dict) -> dict:
        return value


DECLARATION_DATE_FIELDS = [
    "date_invoice",
    "date_payment_emitter",
    "date_payment_recipient",
    "date_start",
    "date_end",
]


def merge_partners(pending: QuerySet, transfer_id) -> set:
    """
    The transfers marked as the same support as the transfer, in the given
    pending declarations.
    """
    merges = (
        pending.filter(kind=DECLARATION_KIND_MERGE)
        .filter(Q(transfer_id=transfer_id) | Q(other_transfers=transfer_id))
        .distinct()
        .prefetch_related("other_transfers")
    )
    partners = set()
    for merge in merges:
        partners |= {
            merge.transfer_id,
            *[t.id for t in merge.other_transfers.all()],
        }
    return partners - {transfer_id, None}


class DeclarationSerializer(serializers.ModelSerializer):
    """
    A change of the organization to its supports. New supports and edits
    declare values, validated on save. Confirmations and removals only refer
    to a transfer. Merges and not-duplicates tell whether the transfer and
    `other_transfers` are the same support, or not: possible duplicates.
    The organization is passed as `entity` in the context.
    """

    transfer_id = serializers.PrimaryKeyRelatedField(
        source="transfer",
        queryset=Transfer.objects.all(),
        allow_null=True,
        required=False,
    )
    recipient_id = serializers.PrimaryKeyRelatedField(
        source="recipient",
        queryset=Entity.objects.all(),
        allow_null=True,
        required=False,
    )
    agent_ids = serializers.PrimaryKeyRelatedField(
        source="agents",
        queryset=Entity.objects.all(),
        many=True,
        required=False,
    )
    # Reconciliation: the transfers merged with `transfer_id`, or that aren't
    # the same support. For a new support, the matches it isn't.
    other_transfer_ids = serializers.PrimaryKeyRelatedField(
        source="other_transfers",
        queryset=Transfer.objects.all(),
        many=True,
        required=False,
    )
    # For a new support, the organization's other new supports it isn't
    other_declaration_ids = serializers.PrimaryKeyRelatedField(
        source="other_declarations",
        queryset=Declaration.objects.all(),
        many=True,
        required=False,
    )
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), allow_null=True, required=False
    )
    date_invoice = PrecisionDateField(allow_null=True, required=False)
    date_payment_emitter = PrecisionDateField(allow_null=True, required=False)
    date_payment_recipient = PrecisionDateField(allow_null=True, required=False)
    date_start = PrecisionDateField(allow_null=True, required=False)
    date_end = PrecisionDateField(allow_null=True, required=False)
    author = serializers.SerializerMethodField()

    class Meta:
        model = Declaration
        fields = [
            "id",
            "kind",
            "status",
            "transfer_id",
            "recipient_id",
            "agent_ids",
            "other_transfer_ids",
            "other_declaration_ids",
            "amount",
            "currency",
            *DECLARATION_DATE_FIELDS,
            "author",
            "date_last_updated",
        ]
        read_only_fields = ["status", "date_last_updated"]

    def get_author(self, obj: Declaration) -> str | None:
        return obj.author.email if obj.author else None

    def validate(self, attrs: dict) -> dict:
        entity = self.context["entity"]
        kind = attrs["kind"]
        if self.instance is not None:
            transfer = attrs.get("transfer", self.instance.transfer)
            # The transfer of a declaration doesn't change, but a new support
            # becomes the confirmation or edit of the transfer it matches
            matched = self.instance.kind == DECLARATION_KIND_NEW and kind in [
                DECLARATION_KIND_CONFIRMATION,
                DECLARATION_KIND_EDIT,
            ]
            if transfer != self.instance.transfer and not matched:
                raise ValidationError(
                    {"transfer_id": "The transfer can't be changed."}
                )
            attrs["transfer"] = transfer
        if kind in DECLARATION_KINDS_SUPPORT_CHANGES:
            attrs["other_transfers"] = []
        attrs.setdefault("other_transfers", [])
        if kind != DECLARATION_KIND_NEW:
            attrs["other_declarations"] = []
        attrs.setdefault("other_declarations", [])
        errors = self.validate_transfer(entity, kind, attrs.get("transfer"))
        if not errors:
            errors = self.validate_other_transfers(
                entity, kind, attrs.get("transfer"), attrs["other_transfers"]
            )
        if not errors:
            errors = self.validate_other_declarations(
                entity, attrs["other_declarations"]
            )
        if kind in DECLARATION_KINDS_WITH_VALUES:
            errors.update(self.validate_values(attrs))
        else:
            # Only the transfer's values are published
            attrs.update(
                recipient=None,
                agents=[],
                amount=None,
                currency=None,
                **{f: None for f in DECLARATION_DATE_FIELDS},
            )
        if errors:
            raise ValidationError(errors)
        return attrs

    def other_pending(self, entity: Entity) -> QuerySet:
        """The organization's other declarations not published yet."""
        pending = Declaration.objects.pending().filter(entity=entity)
        if self.instance is not None:
            pending = pending.exclude(id=self.instance.id)
        return pending

    def validate_transfer(
        self, entity: Entity, kind: str, transfer: Transfer | None
    ) -> dict:
        if kind == DECLARATION_KIND_NEW:
            if transfer is not None:
                return {
                    "transfer_id": "A new support doesn't refer to a transfer."
                }
            return {}
        if transfer is None:
            return {"transfer_id": "Pick the support to change."}
        # Only the organization's own supports: not those of its children,
        # which its table also lists
        if not table_supports(entity).filter(id=transfer.id).exists():
            return {
                "transfer_id": "Only the organization's own supports can be changed."
            }
        if kind in DECLARATION_KINDS_RECONCILIATION:
            return {}
        pending = self.other_pending(entity).filter(
            kind__in=DECLARATION_KINDS_SUPPORT_CHANGES
        )
        if pending.filter(transfer=transfer).exists():
            return {
                "transfer_id": "This support already has a change not published yet."
            }
        # One change for the supports marked as the same support, published
        # on the merged one
        partners = merge_partners(self.other_pending(entity), transfer.id)
        if pending.filter(transfer_id__in=partners).exists():
            return {
                "transfer_id": "This support is marked as the same as another "
                "one, which already has a change not published yet."
            }
        is_source = transfer.data_load_sources.filter(entity=entity).exists()
        if kind == DECLARATION_KIND_CONFIRMATION and is_source:
            return {
                "transfer_id": "The organization already declared this support."
            }
        if kind == DECLARATION_KIND_REMOVAL and not is_source:
            return {
                "transfer_id": "Only the supports that the organization declared can be removed."
            }
        return {}

    def validate_other_declarations(
        self, entity: Entity, others: list[Declaration]
    ) -> dict:
        """The organization's other new supports that a new support isn't."""
        new_supports = self.other_pending(entity).filter(
            kind=DECLARATION_KIND_NEW
        )
        ids = {d.id for d in others}
        if new_supports.filter(id__in=ids).count() != len(ids):
            return {
                "other_declaration_ids": "Only the organization's other new "
                "supports, not published yet."
            }
        return {}

    def validate_other_transfers(
        self,
        entity: Entity,
        kind: str,
        transfer: Transfer | None,
        others: list[Transfer],
    ) -> dict:
        """
        The transfers of a reconciliation: the possible duplicates of a merge
        or not-duplicate, or the matches that a new support isn't.
        """
        if kind in DECLARATION_KINDS_SUPPORT_CHANGES:
            return {}
        field = "other_transfer_ids"
        ids = {t.id for t in others}
        if kind in DECLARATION_KINDS_RECONCILIATION and not ids:
            return {field: "Pick the other support."}
        if transfer is not None and transfer.id in ids:
            return {field: "A support can't be a duplicate of itself."}
        if table_supports(entity).filter(id__in=ids).count() != len(ids):
            return {
                field: "Only the organization's own supports can be reconciled."
            }
        pending = self.other_pending(entity)
        if kind == DECLARATION_KIND_MERGE:
            group = ids | {transfer.id}
            merges = pending.filter(kind=DECLARATION_KIND_MERGE).filter(
                Q(transfer_id__in=group) | Q(other_transfers__in=group)
            )
            if merges.exists():
                return {
                    field: "One of these supports is already marked as the "
                    "same as another one."
                }
            changes = pending.filter(
                kind__in=DECLARATION_KINDS_SUPPORT_CHANGES,
                transfer_id__in=group,
            )
            if changes.count() > 1:
                return {
                    field: "Several of these supports have a change not published "
                    "yet: undo all of them but one first."
                }
        if kind == DECLARATION_KIND_NOT_DUPLICATE and ids & merge_partners(
            pending, transfer.id
        ):
            return {field: "These supports are marked as the same support."}
        return {}

    def validate_values(self, attrs: dict) -> dict:
        """The rules of the `Transfer` model's checks."""
        errors = {}
        if attrs.get("recipient") is None:
            errors["recipient_id"] = "Pick the beneficiary."
        dates = {f: attrs.get(f) for f in DECLARATION_DATE_FIELDS}
        if not any(
            dates[f]
            for f in [
                "date_invoice",
                "date_payment_emitter",
                "date_payment_recipient",
                "date_start",
            ]
        ):
            errors["dates"] = (
                "Enter at least the invoice, sent, received or agreement "
                "start date."
            )
        if bool(dates["date_start"]) != bool(dates["date_end"]):
            errors["date_end"] = (
                "Enter both the agreement start and end dates, or neither."
            )
        elif dates["date_start"] and not date_contains(
            dates["date_start"], None, dates["date_end"]
        ):
            # Compared at the coarser precision of the two dates, as in the
            # matching: it can end in 2024 and start in June 2024
            errors["date_end"] = "The agreement ends before it starts."
        # Required in the Hub, unlike in the ingested data
        amount, currency = attrs.get("amount"), attrs.get("currency")
        if amount is None:
            errors["amount"] = "Enter the amount."
        elif not math.isfinite(amount):
            # Not JSON compliant, e.g. NaN
            errors["amount"] = "Enter a number."
        elif amount <= 0:
            errors["amount"] = "The amount must be positive."
        if currency is None:
            errors["currency"] = "Pick the currency of the amount."
        return errors

    def create(self, validated_data: dict) -> Declaration:
        validated_data.update(
            entity=self.context["entity"], author=self.context["user"]
        )
        return super().create(validated_data)


class EntityDeclarationsView(HubView):
    """
    GET: the organization's declarations not published yet, for its members
    and the TSOSI team. `entities` holds their entities missing from the
    frontend's reference data (see `hub_entities`), `possible_duplicates`
    the pairs of rows of its supports table that may be the same support,
    not reconciled yet: transfer IDs, or `new-<ID>` for new supports.
    POST: save a new declaration, as a draft.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)
        declarations = (
            Declaration.objects.pending()
            .filter(entity=entity)
            .select_related("author")
            .prefetch_related("agents", "other_transfers", "other_declarations")
            .order_by("date_created")
        )
        entity_ids = set()
        for declaration in declarations:
            entity_ids |= {declaration.recipient_id}
            entity_ids |= {a.id for a in declaration.agents.all()}
        serializer = DeclarationSerializer(
            declarations, many=True, context={"entity": entity}
        )
        return Response(
            {
                "declarations": serializer.data,
                "entities": hub_entities(request, entity_ids - {None}),
                "possible_duplicates": possible_duplicates(entity),
            }
        )

    def post(self, request, entity_id: str):
        entity = get_declaring_entity(request.user, entity_id)
        serializer = DeclarationSerializer(
            data=request.data,
            context={"entity": entity, "user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class EntityDeclarationView(HubView):
    """
    PUT: replace a draft declaration of the organization.
    DELETE: remove a draft declaration (undo the change).
    Submitted declarations can't be changed.
    """

    permission_classes = [IsMemberOrStaff]

    def get_draft(self, request, entity_id: str, declaration_id: int):
        """
        The draft, locked until the end of the request's transaction: a
        submission at the same time (`submit_declarations`, which locks the
        drafts too) either waits for the change, then sees it, or submits
        the draft first, which then can't be changed.
        """
        entity = get_declaring_entity(request.user, entity_id)
        try:
            declaration = Declaration.objects.select_for_update().get(
                id=declaration_id, entity=entity
            )
        except Declaration.DoesNotExist:
            raise Http404 from None
        if declaration.status != DECLARATION_STATUS_DRAFT:
            raise PermissionDenied(
                "This change is submitted, it can't be changed any more."
            )
        return entity, declaration

    @transaction.atomic
    def put(self, request, entity_id: str, declaration_id: int):
        entity, declaration = self.get_draft(request, entity_id, declaration_id)
        serializer = DeclarationSerializer(
            declaration,
            data=request.data,
            context={"entity": entity, "user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def delete(self, request, entity_id: str, declaration_id: int):
        _, declaration = self.get_draft(request, entity_id, declaration_id)
        declaration.delete()
        return Response(status=204)
