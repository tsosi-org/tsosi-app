from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from tsosi.api.serializers import (
    AnalyticSerializer,
    CurrencySerializer,
    EntityCoordinatesSerializer,
    EntityDetailsSerializer,
    EntitySerializer,
    TransfertDetailsSerializer,
    TransfertSerializer,
)
from tsosi.app_settings import app_settings
from tsosi.models import Analytic, Currency, Entity, Transfert


class ReadOnlyViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "head", "options"]

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("Create operation is not allowed.")

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("Update operation is not allowed.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Destroy operation is not allowed.")


class BypassPagination(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        if "*" in app_settings.API_BYPASS_PAGINATION_ALLOWED_ORIGINS:
            return super().has_permission(request, view)

        origin = request.META.get("HTTP_ORIGIN")
        if (
            origin
            and origin in app_settings.API_BYPASS_PAGINATION_ALLOWED_ORIGINS
        ):
            return super().has_permission(request, view)
        referer = request.META.get("HTTP_REFERER")
        if referer:
            referer_domain = referer.split("/")[2]
            if (
                referer_domain
                in app_settings.API_BYPASS_PAGINATION_ALLOWED_ORIGINS
            ):
                return super().has_permission(request, view)
        raise PermissionDenied("You are not allowed to bypass pagination.")


class AllActionViewSet(viewsets.ModelViewSet):
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


class EntityViewSet(AllActionViewSet, ReadOnlyViewSet):
    queryset = Entity.objects.filter(is_active=True).prefetch_related(
        "identifiers", "identifiers__registry"
    )
    serializer_class = EntityDetailsSerializer
    filter_backends = [OrderingFilter]
    ordering = ["name"]
    ordering_fields = ["name"]

    @action(
        detail=False, methods=["get"], permission_classes=[BypassPagination]
    )
    def summary(self, request, *args, **kwargs):
        """
        Retrieve all entities with EntitySerializer.
        """
        self.pagination_class = None
        self.serializer_class = EntitySerializer
        return self.list(request, *args, **kwargs)

    @action(
        detail=False, methods=["get"], permission_classes=[BypassPagination]
    )
    def emitters(self, request: Request, *args, **kwargs):
        """ """
        entity_id = request.query_params.get("entity_id")
        if entity_id is None:
            raise ValidationError(f"`entity_id` query parameter if missing.")

        self.pagination_class = None
        self.serializer_class = EntityCoordinatesSerializer
        ids = Transfert.objects.filter(recipient_id=entity_id).values_list(
            "emitter_id", flat=True
        )
        self.queryset = Entity.objects.filter(id__in=ids).distinct()
        return self.list(request, *args, **kwargs)


class TransfertFilter(filters.FilterSet):
    entity_id = filters.CharFilter(method="filter_by_entity")

    class Meta:
        model = Transfert
        fields = ["entity_id"]

    def filter_by_entity(
        self, queryset: QuerySet, name: str, value: str | None
    ) -> QuerySet:
        """
        TODO: Check the perf of doing OR condition with Django ORM.
        It might be way more efficient to perform separate requests on each
        condition and then UNION them
        """
        if value is None or not value:
            raise ValidationError(
                detail=f"Query parameter value for `entity_id` is not accepted: {value}"
            )
        condition = (
            Q(emitter_id=value) | Q(recipient_id=value) | Q(agent_id=value)
        )
        return queryset.filter(condition)


class TransfertViewSet(AllActionViewSet, ReadOnlyViewSet):
    queryset = Transfert.objects.all().select_related(
        "emitter", "recipient", "agent"
    )
    serializer_class = TransfertSerializer
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = TransfertFilter
    ordering = ["date_clc"]
    ordering_fields = ["date_clc"]

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = TransfertDetailsSerializer
        return super().retrieve(request, *args, **kwargs)


class CurrencyViewSet(ReadOnlyViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    pagination_class = None


class AnalyticViewSet(ReadOnlyViewSet):
    queryset = Analytic.objects.all()
    pagination_class = None
    serializer_class = AnalyticSerializer
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["recipient_id", "country", "year"]
