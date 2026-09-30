from rest_framework import serializers

from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX
from tsosi.models import (
    Analytic,
    Currency,
    DataLoadSource,
    Entity,
    EntityEditAccess,
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


class EntityEditIdentifiersSerializer(serializers.Serializer):
    ror = serializers.RegexField(
        ROR_ID_REGEX, required=False, allow_null=True, allow_blank=True
    )
    wikidata = serializers.RegexField(
        WIKIDATA_ID_REGEX, required=False, allow_null=True, allow_blank=True
    )

    # Prefixes users are likely to paste along with the identifier
    ID_PREFIXES = {
        "ror": ["https://ror.org/", "http://ror.org/", "ror.org/"],
        "wikidata": [
            "https://www.wikidata.org/wiki/",
            "http://www.wikidata.org/wiki/",
            "www.wikidata.org/wiki/",
        ],
    }

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = dict(data)
            for registry, prefixes in self.ID_PREFIXES.items():
                value = data.get(registry)
                if not isinstance(value, str):
                    continue
                value = value.strip()
                for prefix in prefixes:
                    value = value.removeprefix(prefix)
                data[registry] = value
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = {k: v or None for k, v in attrs.items()}
        entity: Entity = self.context["entity"]
        for registry, value in attrs.items():
            current = entity.identifiers.filter(registry_id=registry).first()
            if current is not None:
                if value != current.value:
                    raise serializers.ValidationError(
                        {
                            registry: "The identifier can't be changed nor "
                            "removed. Please contact us."
                        }
                    )
                continue
            if value is None:
                continue
            existing = Identifier.objects.filter(
                registry_id=registry, value=value
            ).first()
            if existing is not None and existing.entity_id != entity.id:
                raise serializers.ValidationError(
                    {
                        registry: "This identifier is already attached to "
                        "another entity. Please contact us."
                    }
                )
        return attrs


class EntityEditInfrastructureSerializer(serializers.Serializer):
    support_url = serializers.URLField(
        max_length=256, required=False, allow_null=True
    )
    posi_url = serializers.URLField(
        max_length=256, required=False, allow_null=True
    )
    infra_finder_url = serializers.URLField(
        max_length=256, required=False, allow_null=True
    )
    date_scoss_start = serializers.DateField(required=False, allow_null=True)
    date_scoss_end = serializers.DateField(required=False, allow_null=True)

    def to_internal_value(self, data):
        # Empty strings are considered as null values
        if isinstance(data, dict):
            data = {k: (None if v == "" else v) for k, v in data.items()}
        return super().to_internal_value(data)

    def validate(self, attrs):
        start = attrs.get("date_scoss_start")
        end = attrs.get("date_scoss_end")
        if ("date_scoss_start" in attrs) != ("date_scoss_end" in attrs) or (
            (start is None) != (end is None)
        ):
            raise serializers.ValidationError(
                "Both SCOSS start and end dates must be provided."
            )
        if start is not None and end is not None and start > end:
            raise serializers.ValidationError(
                "SCOSS start date must be before the end date."
            )
        return attrs


class EntityEditSerializer(serializers.Serializer):
    """
    Validates the data sent to edit an entity.
    """

    name = serializers.CharField(max_length=512, required=False)
    short_name = serializers.CharField(
        max_length=128, required=False, allow_null=True, allow_blank=True
    )
    country = serializers.RegexField(
        r"^[A-Z]{2}$", required=False, allow_null=True, allow_blank=True
    )
    date_inception = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(
        max_length=5000, required=False, allow_null=True, allow_blank=True
    )
    is_barcelona = serializers.BooleanField(required=False)
    website = serializers.URLField(
        max_length=256, required=False, allow_null=True, allow_blank=True
    )
    wikipedia_url = serializers.RegexField(
        r"^https://[a-z\-]+\.wikipedia\.org/wiki/.+$",
        max_length=512,
        required=False,
        allow_null=True,
        allow_blank=True,
        error_messages={
            "invalid": "Enter a Wikipedia page URL, ex: "
            "https://en.wikipedia.org/wiki/Page_name"
        },
    )
    identifiers = EntityEditIdentifiersSerializer(required=False)
    infrastructure = EntityEditInfrastructureSerializer(required=False)

    def to_internal_value(self, data):
        # Empty date strings are considered as null values
        if isinstance(data, dict) and data.get("date_inception") == "":
            data = {**data, "date_inception": None}
        return super().to_internal_value(data)

    def validate(self, attrs):
        # Blank strings are stored as null values
        for field in [
            "short_name",
            "country",
            "description",
            "website",
            "wikipedia_url",
        ]:
            if field in attrs and not attrs[field]:
                attrs[field] = None
        return attrs


class EntityEditAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityEditAccess
        fields = ["email", "date_expires"]
