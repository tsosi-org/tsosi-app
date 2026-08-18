from urllib.parse import urlparse

from django.db.models import QuerySet
from django.http import Http404, HttpResponseRedirect
from django.urls import resolve as django_resolve
from django.urls import reverse as django_reverse
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from tsosi.api.serializers import (
    AnalyticSerializer,
    CurrencySerializer,
    EntityDetailsSerializer,
    EntitySerializer,
    TransferDetailsSerializer,
    TransferSerializer,
)
from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Analytic, Currency, Entity, Transfer


class RedirectRequired(Exception):
    def __init__(self, query=None, **kwargs):
        self.query = query
        self.kwargs = kwargs


class BypassPagination(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        if "*" in app_settings.API_BYPASS_PAGINATION_ALLOWED_ORIGINS:
            return super().has_permission(request, view)

        origin: str | None = request.META.get(
            "HTTP_ORIGIN"
        ) or request.META.get("HTTP_REFERER")
        if (
            origin
            and urlparse(origin).hostname
            in app_settings.API_BYPASS_PAGINATION_ALLOWED_ORIGINS
        ):
            return super().has_permission(request, view)

        raise PermissionDenied("You are not allowed to bypass pagination.")


class AllActionViewSet(viewsets.GenericViewSet):
    @action(
        detail=False, methods=["get"], permission_classes=[BypassPagination]
    )
    def all(self, request, *args, **kwargs):
        """
        Retrieve all data without pagination.
        Restricted to requests with permission.
        """
        self.pagination_class = None
        return self.list(request, *args, **kwargs)


class EntityViewSet(viewsets.ReadOnlyModelViewSet, AllActionViewSet):
    queryset = (
        Entity.objects.filter(is_active=True)
        .prefetch_related("identifiers")
        .select_related("infrastructure_details")
    )
    serializer_class = EntitySerializer
    filter_backends = [SearchFilter]
    search_fields = ["name", "short_name", "names__value", "identifiers__value"]

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except RedirectRequired as e:
            resolved = django_resolve(request.path)
            return HttpResponseRedirect(
                django_reverse(
                    f"{resolved.app_names[0]}:{resolved.url_name}",
                    kwargs={**e.kwargs},
                )
                + (
                    f"?{request.META.get('QUERY_STRING', '')}"
                    if request.GET
                    else ""
                )
            )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EntityDetailsSerializer
        return super().get_serializer_class()

    def get_object(self):
        """
        We allow multiple way to reference an entity.
        It can be its database ID (default DRF way) or by using an external
        unique identifier.
        We redirect when the identifier is outdated.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        id_value = self.kwargs[lookup_url_kwarg]
        try:
            entity = Entity.objects.get_by_any_id(id_value).sucessor_or_self()
        except Entity.DoesNotExist:
            raise Http404

        if entity.is_active is False:
            raise Http404

        identifier = entity.identifiers.filter(
            registry_id=REGISTRY_TSOSI
        ).first()
        if identifier and identifier.value != id_value:
            raise RedirectRequired(**{lookup_url_kwarg: identifier.value})

        self.kwargs[lookup_url_kwarg] = entity.id

        return super().get_object()


class TransferFilter(filters.FilterSet):
    entity_id = filters.CharFilter(method="filter_by_entity")

    class Meta:
        model = Transfer
        fields = ["entity_id"]

    def filter_by_entity(
        self, queryset: QuerySet, name: str, value: str | None
    ) -> QuerySet:
        try:
            return queryset.filter_by_entity(value)
        except Entity.DoesNotExist:
            raise Http404


class TransferViewSet(viewsets.ReadOnlyModelViewSet, AllActionViewSet):
    queryset = (
        Transfer.objects.filter(merged_into__isnull=True, is_future=False)
        .select_related("emitter", "recipient")
        .prefetch_related("agents")
    )
    serializer_class = TransferSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransferFilter

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = TransferDetailsSerializer
        return super().retrieve(request, *args, **kwargs)


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    pagination_class = None


class AnalyticViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Analytic.objects.all()
    pagination_class = None
    serializer_class = AnalyticSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ["recipient_id", "country", "year"]
