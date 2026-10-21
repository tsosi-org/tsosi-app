"""
Access to the Hub: the members of an organization and the TSOSI team, the
base view, and the entities as the Hub shows them.
"""

from django.db.models import (
    BooleanField,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Q,
    QuerySet,
)
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.views import APIView

from tsosi.api.serializers import IdentifierSerializer
from tsosi.models import Entity, Membership, Transfer


def get_membership(user) -> Membership | None:
    """Return the active membership of the user, if any."""
    if not user.is_authenticated:
        return None
    return (
        Membership.objects.active()
        .select_related("entity")
        .filter(user=user)
        .first()
    )


def can_edit_entity(user, entity: Entity) -> bool:
    """
    Whether the user can edit the entity's profile: a member of that entity,
    or the TSOSI team.
    """
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    membership = get_membership(user)
    return membership is not None and membership.entity_id == entity.id


def get_hub_entity(user, entity_id: str) -> Entity:
    try:
        entity = Entity.objects.get_by_any_id(entity_id)
    except Entity.DoesNotExist:
        raise Http404 from None
    entity = entity.sucessor_or_self()
    if not can_edit_entity(user, entity):
        raise Http404
    return entity


def get_declaring_entity(user, entity_id: str) -> Entity:
    """
    The organization of a Hub URL, for the users who can change its
    supports: its members with the "Can declare supports" option. The TSOSI
    team only reads them.
    """
    entity = get_hub_entity(user, entity_id)
    membership = get_membership(user)
    if (
        membership is None
        or membership.entity_id != entity.id
        or not membership.can_declare_supports
    ):
        raise PermissionDenied(
            "Only the organization's members can change its supports."
        )
    return entity


class IsOrganizationMember(BasePermission):
    """The user is logged in and an active member of an organization."""

    def has_permission(self, request, view) -> bool:
        return get_membership(request.user) is not None


class IsMemberOrStaff(BasePermission):
    """The user is logged in, and a member of an organization or staff."""

    def has_permission(self, request, view) -> bool:
        return request.user.is_staff or get_membership(request.user) is not None


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HubView(APIView):
    """
    Base view of the Hub: session authentication, members only, and
    CSRF checks on all write requests, anonymous ones included.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOrganizationMember]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in SAFE_METHODS:
            SessionAuthentication().enforce_csrf(request)


def with_hub_status(entities: QuerySet) -> QuerySet:
    """
    Annotate the entities with whether they're public, and whether they were
    added in the Hub and have no published support yet.
    """
    in_transfer = Exists(
        Transfer.objects.filter(
            Q(emitter=OuterRef("pk"))
            | Q(recipient=OuterRef("pk"))
            | Q(agents=OuterRef("pk"))
        )
    )
    added_in_hub = Exists(
        Entity.objects.filter(entities_added_in_hub=OuterRef("pk"))
    )
    return entities.prefetch_related("identifiers").annotate(
        is_public=Exists(Entity.objects.public().filter(pk=OuterRef("pk"))),
        is_new=ExpressionWrapper(
            Q(added_in_hub) & ~Q(in_transfer), output_field=BooleanField()
        ),
    )


class HubEntitySerializer(serializers.ModelSerializer):
    """
    An entity in the Hub, public or not, with its scope. `is_new`: added in
    the Hub, without published support yet. The entities must come from
    `with_hub_status`.
    """

    identifiers = IdentifierSerializer(many=True)
    is_public = serializers.BooleanField()
    is_new = serializers.BooleanField()

    class Meta:
        model = Entity
        fields = [
            "id",
            "name",
            "short_name",
            "country",
            "icon",
            "identifiers",
            "is_recipient",
            "scope",
            "is_public",
            "is_new",
        ]


def hub_entities(request, entity_ids: set) -> dict[str, dict]:
    """
    The given entities missing from the frontend's reference data, by ID:
    those not on the public site, and those with a scope it can't tell. It
    only tells that the public beneficiaries are in scope, so it lacks the
    scope of the others, e.g. a beneficiary to be checked that is public for
    another role.
    """
    entities = with_hub_status(Entity.objects.filter(id__in=entity_ids)).filter(
        Q(is_public=False) | Q(scope__isnull=False, is_recipient=False)
    )
    serializer = HubEntitySerializer(
        entities, many=True, context={"request": request}
    )
    return {str(e["id"]): e for e in serializer.data}
