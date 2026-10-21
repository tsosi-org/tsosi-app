"""
The organization's saved supports that may be the one being entered.
"""

from rest_framework import serializers
from rest_framework.response import Response

from tsosi.api.hub.base import HubView, IsMemberOrStaff, get_hub_entity
from tsosi.api.hub.declarations import PrecisionDateField
from tsosi.data.hub_reconciliation import declared_transfer, find_matches
from tsosi.models import Currency, Entity


class MatchQuerySerializer(serializers.Serializer):
    """The values of a support being declared, typed as for a declaration."""

    recipient_id = serializers.PrimaryKeyRelatedField(
        source="recipient", queryset=Entity.objects.all()
    )
    amount = serializers.FloatField(allow_null=True, required=False)
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), allow_null=True, required=False
    )
    date_invoice = PrecisionDateField(required=False)
    date_payment_emitter = PrecisionDateField(required=False)
    date_payment_recipient = PrecisionDateField(required=False)
    date_start = PrecisionDateField(required=False)
    date_end = PrecisionDateField(required=False)
    # The row being edited, a new support, which isn't its own match
    exclude = serializers.CharField(required=False)


class EntityMatchesView(HubView):
    """
    GET: the organization's saved supports (published, or new ones not
    published yet) that may be the support described by the query, entered
    as a new support (beneficiary, amount, currency and dates, typed as for
    a declaration), with whether their amount differs: reconciliation while
    entering data. Their rows are transfer IDs, or `new-<ID>`.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request, entity_id: str):
        entity = get_hub_entity(request.user, entity_id)
        serializer = MatchQuerySerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        exclude = values.pop("exclude", None)
        transfer = declared_transfer(entity, **values)
        return Response(
            {
                "matches": [
                    {"row_id": key, "amount_differs": differs}
                    for key, differs in find_matches(entity, transfer, exclude)
                ]
            }
        )
