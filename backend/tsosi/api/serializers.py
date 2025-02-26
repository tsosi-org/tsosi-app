from rest_framework import serializers
from tsosi.models import Analytic, Currency, Entity, Identifier, Transfert


class IdentifierSerializer(serializers.ModelSerializer):
    registry = serializers.ReadOnlyField(source="registry_id")
    # registry_url = serializers.SerializerMethodField()

    class Meta:
        model = Identifier
        fields = [
            "registry",
            "value",
            # "registry_url"
        ]

    # def get_registry_url(self, obj: Identifier) -> str:
    #     return obj.registry.link_template.format(id=obj.value)


class BaseEntitySerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(many=True)


class EntitySerializer(BaseEntitySerializer):
    """
    Minified serializer for entities.
    """

    class Meta:
        model = Entity
        fields = ["id", "name", "country", "identifiers", "coordinates", "logo"]
        extra_kwargs = {
            "url": {"view_name": "tsosi:entity-detail"},  # Use namespaced URL
        }


class EntityDetailsSerializer(BaseEntitySerializer):
    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "country",
            "website",
            "description",
            "logo",
            "wikipedia_url",
            "wikipedia_extract",
            "identifiers",
            "coordinates",
            "is_emitter",
            "is_recipient",
            "is_agent",
            "infra_finder_url",
            "posi_url",
            "is_scoss_awarded",
        ]
        extra_kwargs = {
            "url": {"view_name": "tsosi:entity-detail"},  # Use namespaced URL
        }


class BaseTransfertSerializer(serializers.ModelSerializer):
    """
    Base serializer for transferts. It overloads amount-related
    properties to return null if the amount should be hidden.
    """

    amount = serializers.SerializerMethodField()
    amounts_clc = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    raw_data = serializers.SerializerMethodField()

    def get_amount(self, obj: Transfert):
        return None if obj.hide_amount else obj.amount

    def get_amounts_clc(self, obj: Transfert):
        return None if obj.hide_amount else obj.amounts_clc

    def get_currency(self, obj: Transfert):
        return None if obj.hide_amount else obj.currency_id

    def get_raw_data(self, obj: Transfert):
        if not obj.hide_amount:
            return obj.raw_data
        data = obj.raw_data
        data.pop(obj.original_amount_field, None)
        return data


class TransfertSerializer(BaseTransfertSerializer):
    class Meta:
        model = Transfert
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


class TransfertDetailsSerializer(BaseTransfertSerializer):
    class Meta:
        model = Transfert
        fields = [
            "id",
            "emitter_id",
            "recipient_id",
            "agent_id",
            "amount",
            "currency",
            "date_clc",
            "date_invoice",
            "date_payment",
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
