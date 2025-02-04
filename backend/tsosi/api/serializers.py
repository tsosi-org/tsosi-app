from rest_framework import serializers
from tsosi.models import Currency, Entity, Identifier, Transfert


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


class EntityDetailsSerializer(serializers.HyperlinkedModelSerializer):
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "country",
            "website",
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


class EntitySerializer(serializers.ModelSerializer):
    """
    Minified serializer for entities.
    """

    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Entity
        fields = ["id", "name", "country", "identifiers"]
        extra_kwargs = {
            "url": {"view_name": "tsosi:entity-detail"},  # Use namespaced URL
        }


class TransfertSerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField(source="currency_id")

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


class TransfertDetailsSerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField(source="currency_id")

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
