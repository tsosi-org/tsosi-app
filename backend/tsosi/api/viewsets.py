import re
from urllib.parse import urlparse

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
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
from tsosi.models import Analytic, Currency, Entity, Transfer
from tsosi.models.static_data import PID_REGEX_OPTIONS
from tsosi.models.utils import UUID4_REGEX


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
    serializer_class = EntitySerializer
    filter_backends = [OrderingFilter, SearchFilter]
    ordering = ["-is_recipient", "name"]
    ordering_fields = ["name", "is_recipient"]
    search_fields = ["name", "short_name", "names__value", "identifiers__value"]

    @action(
        detail=False, methods=["get"], permission_classes=[BypassPagination]
    )
    def emitters(self, request: Request, *args, **kwargs):
        """ """
        entity_id = request.query_params.get("entity_id")
        if entity_id is None:
            raise ValidationError(f"`entity_id` query parameter if missing.")

        self.pagination_class = None
        ids = Transfer.objects.filter(
            merged_into__isnull=True, recipient_id=entity_id
        ).values_list("emitter_id", flat=True)
        self.queryset = Entity.objects.filter(id__in=ids).distinct()
        return self.list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EntityDetailsSerializer
        return super().get_serializer_class()

    def get_object(self):
        """
        We allow multiple way to reference an entity.
        It can be its database ID (default DRF way) or by using an external
        unique identifier.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        # Implement the correct lookup according to the parameter value
        filter_kwargs = {}
        id_value: str = self.kwargs[lookup_url_kwarg]
        if re.match(UUID4_REGEX, id_value):
            filter_kwargs[self.lookup_field] = id_value
        else:
            for r_id, r_pattern in PID_REGEX_OPTIONS:
                if not re.match(r_pattern, id_value):
                    continue

                filter_kwargs["identifiers__registry_id"] = r_id
                filter_kwargs["identifiers__value"] = id_value
                break

        assert filter_kwargs, "The given ID does not match the expected format."

        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class TransferFilter(filters.FilterSet):
    entity_id = filters.CharFilter(method="filter_by_entity")

    class Meta:
        model = Transfer
        fields = ["entity_id"]

    def filter_by_entity(
        self, queryset: QuerySet, name: str, value: str | None
    ) -> QuerySet:
        """
        TODO: Check the perf of doing OR condition with Django ORM.
        It might be way more efficient to perform separate requests on each
        condition and then UNION them
        TODO: Recursive query should be made in raw postgresql
        """
        if value is None or not value:
            raise ValidationError(
                detail=f"Query parameter value for `entity_id` is not accepted: {value}"
            )
        value_and_childs = {value} | set(
            Entity.objects.get(id=value)
            .get_all_children()
            .values_list("id", flat=True)
        )
        condition = (
            Q(emitter_id__in=value_and_childs)
            | Q(recipient_id=value)
            | Q(agent_id=value)
        )
        return queryset.filter(condition)


class TransferViewSet(AllActionViewSet, ReadOnlyViewSet):
    queryset = Transfer.objects.filter(merged_into__isnull=True).select_related(
        "emitter", "recipient", "agent"
    )
    serializer_class = TransferSerializer
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = TransferFilter
    ordering = ["date_clc"]
    ordering_fields = ["date_clc"]

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = TransferDetailsSerializer
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
