"""
The organizations to pick as beneficiary or intermediary: searched in TSOSI,
looked up in ROR or Wikidata, and added when missing.
"""

from collections.abc import Callable

from django.core.cache import cache
from django.db.models import Case, Exists, OuterRef, Q, QuerySet, When
from rest_framework import serializers
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from tsosi.api.hub.base import (
    HubEntitySerializer,
    HubView,
    IsMemberOrStaff,
    get_declaring_entity,
    with_hub_status,
)
from tsosi.data.entity_edit import create_hub_entity
from tsosi.data.pid_registry.lookup import (
    REGISTRY_NAMES,
    OrganizationRecord,
    RegistryError,
    fetch_organization_record,
    parse_organization_id,
)
from tsosi.models import Entity, Identifier


class RegistryThrottle(UserRateThrottle):
    """The requests to ROR or Wikidata, and the organizations added."""

    scope = "hub_registry"
    rate = "120/hour"


class RegistryUnavailable(APIException):
    status_code = 503
    default_detail = "The registry couldn't be reached. Please try again later."


SEARCH_RESULTS_COUNT = 20
# The registry records are looked up again at each keystroke of the search,
# and when the organization is added
RECORD_CACHE_SECONDS = 3600


def search_entities(query: str) -> QuerySet:
    """
    The active entities, public or not, matching every word of the query in
    their name, short name or other names, or with the query as identifier.
    Exact matches first, then those starting with it.
    """
    condition = Q()
    for word in query.split():
        condition &= (
            Q(name__icontains=word)
            | Q(short_name__icontains=word)
            | Q(names__value__icontains=word)
            | Q(identifiers__value__iexact=word)
        )
    exact_id = Exists(
        Identifier.objects.filter(entity=OuterRef("pk"), value__iexact=query)
    )
    entities = Entity.objects.filter(
        is_active=True, id__in=Entity.objects.filter(condition).values("id")
    )
    return (
        with_hub_status(entities)
        .annotate(
            rank=Case(
                When(exact_id, then=0),
                When(
                    Q(name__iexact=query) | Q(short_name__iexact=query), then=0
                ),
                When(
                    Q(name__istartswith=query)
                    | Q(short_name__istartswith=query),
                    then=1,
                ),
                default=2,
            )
        )
        .order_by("rank", "name")[:SEARCH_RESULTS_COUNT]
    )


def entity_with_identifier(registry: str, value: str) -> Entity | None:
    identifier = (
        Identifier.objects.filter(registry_id=registry, value=value)
        .select_related("entity")
        .first()
    )
    if identifier is None:
        return None
    return identifier.entity.sucessor_or_self()


def fetch_record(
    registry: str, value: str, allow_fetch: Callable[[], bool] | None = None
) -> OrganizationRecord | None:
    """
    The record of the ROR or Wikidata ID, or None if there's none. Cached:
    see `RECORD_CACHE_SECONDS`. `allow_fetch` throttles the requests to the
    registry, the cached records excepted.
    """
    key = f"hub_registry_record:{registry}:{value}"
    record = cache.get(key)
    if record is None:
        if allow_fetch is not None and not allow_fetch():
            raise Throttled()
        try:
            # False when there's no record, as None means not cached
            record = fetch_organization_record(registry, value) or False
        except RegistryError as e:
            raise RegistryUnavailable(
                f"{REGISTRY_NAMES[registry]} couldn't be reached. Please try "
                "again later."
            ) from e
        cache.set(key, record, RECORD_CACHE_SECONDS)
    return record or None


def no_record_message(registry: str) -> str:
    return f"No {REGISTRY_NAMES[registry]} record has this ID."


def lookup_identifier(
    registry: str, value: str, allow_fetch: Callable[[], bool] | None = None
) -> tuple[Entity | None, OrganizationRecord | None]:
    """
    Who has the ROR or Wikidata ID: the TSOSI entity with this ID, or with
    the other ID of its record, or else the organization of its record.
    Both are None if there's no record with this ID.
    """
    entity = entity_with_identifier(registry, value)
    if entity is not None:
        return entity, None
    record = fetch_record(registry, value, allow_fetch)
    if record is None:
        return None, None
    for other_registry, other_value in record.other_ids.items():
        entity = entity_with_identifier(other_registry, other_value)
        if entity is not None:
            return entity, None
    return None, record


def record_data(registry: str, record: OrganizationRecord) -> dict:
    return {
        "registry": registry,
        "identifier": record.id,
        "name": record.name,
        "country": record.country,
        "website": record.website,
    }


class NewOrganizationSerializer(serializers.Serializer):
    """An organization to add: its name, or its ROR or Wikidata ID."""

    name = serializers.CharField(max_length=512, required=False)
    # A ROR or Wikidata ID, or its URL
    identifier = serializers.CharField(required=False)

    def validate_identifier(self, value: str) -> tuple[str, str]:
        parsed_id = parse_organization_id(value)
        if parsed_id is None:
            raise ValidationError(
                "Enter a ROR ID, like 02feahw73, or a Wikidata ID, like Q42."
            )
        return parsed_id

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("identifier") and not attrs.get("name", "").strip():
            raise ValidationError({"name": "Enter the organization's name."})
        return attrs


class OrganizationSearchView(HubView):
    """
    GET: the organizations matching `search`, public or not, with their
    scope, to pick the beneficiary and intermediaries of a support. When the
    query is a ROR or Wikidata ID (or its URL) missing from TSOSI, `lookup`
    holds its record, to add the organization, or the error.
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request):
        query = request.query_params.get("search", "").strip()
        if not query:
            return Response({"results": [], "lookup": None})
        parsed_id = parse_organization_id(query)
        if parsed_id is not None:
            query = parsed_id[1]
        entities = list(search_entities(query))
        lookup = None
        if parsed_id is not None and not any(
            i.value.lower() == query.lower()
            for e in entities
            for i in e.identifiers.all()
        ):
            lookup = self.lookup(request, *parsed_id)
            if isinstance(lookup, Entity):
                entities.insert(0, lookup)
                lookup = None
        return Response(
            {
                "results": HubEntitySerializer(
                    entities, many=True, context={"request": request}
                ).data,
                "lookup": lookup,
            }
        )

    def lookup(self, request, registry: str, value: str) -> Entity | dict:
        """
        The entity with the other ID of the ID's record, or the record, or
        the error, as `{"registry", "identifier", "record", "error"}`.
        """
        result = {
            "registry": registry,
            "identifier": value,
            "record": None,
            "error": None,
        }
        throttle = RegistryThrottle()
        try:
            entity, record = lookup_identifier(
                registry,
                value,
                allow_fetch=lambda: throttle.allow_request(request, self),
            )
        except Throttled:
            result["error"] = "Too many lookups. Please try again later."
            return result
        except RegistryUnavailable as e:
            result["error"] = str(e.detail)
            return result
        if entity is not None:
            return with_hub_status(Entity.objects.filter(id=entity.id)).get()
        if record is None:
            result["error"] = no_record_message(registry)
        else:
            result["record"] = record_data(registry, record)
        return result


class EntityOrganizationsView(HubView):
    """
    POST: add an organization missing from TSOSI, to use it as the
    beneficiary or an intermediary of the organization's supports: from its
    ROR or Wikidata ID, with the name and country of its record, or else
    from its name. It's not public until a support to it is published.
    With the ID of an organization already in TSOSI, that one is returned:
    if it was also added in the Hub and has no published support yet, this
    organization is recorded as having added it too.
    """

    permission_classes = [IsMemberOrStaff]
    throttle_classes = [RegistryThrottle]

    def post(self, request, entity_id: str):
        organization = get_declaring_entity(request.user, entity_id)
        serializer = NewOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data.get("identifier")
        status = 201
        if identifier is None:
            entity = create_hub_entity(
                organization,
                request.user,
                name=serializer.validated_data["name"].strip(),
            )
        else:
            entity, record = lookup_identifier(*identifier)
            if entity is not None:
                status = 200
                # Added by another organization, without published support
                # yet: this one adds it too
                if (
                    with_hub_status(Entity.objects.filter(id=entity.id))
                    .get()
                    .is_new
                ):
                    entity.added_in_hub_by.add(organization)
            elif record is None:
                raise ValidationError(
                    {"identifier": no_record_message(identifier[0])}
                )
            else:
                entity = create_hub_entity(
                    organization,
                    request.user,
                    name=record.name or identifier[1],
                    country=record.country,
                    website=record.website,
                    identifier=identifier,
                )
        entity = with_hub_status(Entity.objects.filter(id=entity.id)).get()
        return Response(
            HubEntitySerializer(entity, context={"request": request}).data,
            status=status,
        )
