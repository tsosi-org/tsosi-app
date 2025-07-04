from rest_framework import serializers
from tsosi.models import (
    Analytic,
    Currency,
    Entity,
    Identifier,
    InfrastructureDetails,
    Transfer,
)


class IdentifierSerializer(serializers.ModelSerializer):
    registry = serializers.ReadOnlyField(source="registry_id")

    class Meta:
        model = Identifier
        fields = [
            "registry",
            "value",
        ]


class InfrastructureDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfrastructureDetails
        fields = "__all__"


class BaseEntitySerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(many=True)


class EntitySerializer(BaseEntitySerializer):
    """
    Minified serializer for entities.
    """

    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "short_name",
            "country",
            "identifiers",
            "coordinates",
            "logo",
            "icon",
            "is_recipient",
            "is_partner",
        ]
        extra_kwargs = {
            "url": {"view_name": "tsosi:entity-detail"},  # Use namespaced URL
        }


class EntityDetailsSerializer(BaseEntitySerializer):
    infrastructure = InfrastructureDetailsSerializer(
        source="infrastructure_details", required=False
    )

    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "short_name",
            "country",
            "website",
            "date_inception",
            "description",
            "logo",
            "icon",
            "wikipedia_url",
            "wikipedia_extract",
            "identifiers",
            "coordinates",
            "is_emitter",
            "is_recipient",
            "is_agent",
            "infrastructure",
            "is_partner",
        ]


class BaseTransferSerializer(serializers.ModelSerializer):
    """
    Base serializer for transfers. It overloads amount-related
    properties to return null if the amount should be hidden.
    """

    amount = serializers.SerializerMethodField()
    amounts_clc = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    raw_data = serializers.SerializerMethodField()

    def get_amount(self, obj: Transfer):
        return None if obj.hide_amount else obj.amount

    def get_amounts_clc(self, obj: Transfer):
        return None if obj.hide_amount else obj.amounts_clc

    def get_currency(self, obj: Transfer):
        return None if obj.hide_amount else obj.currency_id  # type:ignore

    def get_raw_data(self, obj: Transfer):
        if not obj.hide_amount:
            return obj.raw_data
        data: dict = obj.raw_data
        data.pop(obj.original_amount_field, None)
        return data


class TransferSerializer(BaseTransferSerializer):
    class Meta:
        model = Transfer
        fields = [
            "id",
            "emitter_id",
            "recipient_id",
            "agent_id",
            "amount",
            "currency",
            "date_clc",
            "description",
            "amounts_clc",
        ]


class TransferDetailsSerializer(BaseTransferSerializer):
    class Meta:
        model = Transfer
        fields = [
            "id",
            "emitter_id",
            "recipient_id",
            "agent_id",
            "amount",
            "currency",
            "date_clc",
            "date_invoice",
            "date_payment_recipient",
            "date_payment_emitter",
            "date_start",
            "date_end",
            "amounts_clc",
            "raw_data",
        ]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "name"]


class AnalyticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analytic
        fields = "__all__"
