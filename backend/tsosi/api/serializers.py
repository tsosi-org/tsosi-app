from rest_framework import serializers
from tsosi.models import (
    Analytic,
    Currency,
    DataLoadSource,
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
        fields = [
            "infra_finder_url",
            "posi_url",
            "support_url",
            "date_scoss_start",
            "date_scoss_end",
            "legal_entity_wikidata_id",
        ]


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
            "is_emitter",
            "is_agent",
            "is_recipient",
            "is_partner",
            "is_scoss",
            "is_posi",
            "is_barcelona",
            "ror_types",
        ]


class EntityDetailsSerializer(BaseEntitySerializer):
    infrastructure = InfrastructureDetailsSerializer(
        source="infrastructure_details", required=False
    )
    date_data_update = serializers.SerializerMethodField(read_only=True)

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
            "is_partner",
            "is_emitter",
            "is_agent",
            "is_recipient",
            "is_scoss",
            "is_posi",
            "is_barcelona",
            "date_inception",
            "description",
            "website",
            "wikipedia_url",
            "wikipedia_extract",
            "infrastructure",
            "date_data_update",
            "ror_types",
            "children",
        ]

    def get_date_data_update(self, obj):
        dls = (
            DataLoadSource.objects.filter(entity=obj)
            .order_by("-date_data_obtained")
            .values_list("date_data_obtained", flat=True)
            .first()
        )
        return dls


class BaseTransferSerializer(serializers.ModelSerializer):
    """
    Base serializer for transfers. It overloads amount-related
    properties to return null if the amount should be hidden.
    """

    amount = serializers.SerializerMethodField()
    amounts_clc = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    raw_data = serializers.SerializerMethodField()

    def _amount_hidden(self, obj: Transfer) -> bool:
        """
        A transfer's amount is hidden unless the transfer itself allows it,
        or one of its entities is a partner who opted into showing amounts.
        """
        if not obj.hide_amount:
            return False
        entities = [obj.emitter, obj.recipient, *obj.agents.all()]
        return not any(a.is_partner and not a.hide_amount for a in entities)

    def get_amount(self, obj: Transfer):
        return None if self._amount_hidden(obj) else obj.amount

    def get_amounts_clc(self, obj: Transfer):
        return None if self._amount_hidden(obj) else obj.amounts_clc

    def get_currency(self, obj: Transfer):
        return (
            None if self._amount_hidden(obj) else obj.currency_id
        )  # type:ignore

    def get_raw_data(self, obj: Transfer):
        if not self._amount_hidden(obj):
            return obj.raw_data
        data = obj.raw_data
        data.pop(obj.original_amount_field, None)
        for field in data:
            if isinstance(data[field], dict):
                data[field].pop(obj.original_amount_field, None)
        return data


class TransferSerializer(BaseTransferSerializer):
    agent_ids = serializers.PrimaryKeyRelatedField(
        source="agents", many=True, read_only=True
    )

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
            "description",
        ]


class TransferDetailsSerializer(BaseTransferSerializer):
    agent_ids = serializers.PrimaryKeyRelatedField(
        source="agents", many=True, read_only=True
    )
    source_ids = serializers.SlugRelatedField(
        source="data_load_sources",
        many=True,
        read_only=True,
        slug_field="entity_id",
    )

    class Meta:
        model = Transfer
        fields = [
            "id",
            "emitter_id",
            "emitter_sub",
            "recipient_id",
            "agent_ids",
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
            "source_ids",
        ]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "name"]


class AnalyticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analytic
        fields = "__all__"
