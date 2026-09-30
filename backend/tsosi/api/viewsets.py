import json
from urllib.parse import urlparse

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.http import Http404, HttpResponseRedirect
from django.urls import resolve as django_resolve
from django.urls import reverse as django_reverse
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from tsosi.api.serializers import (
    AnalyticSerializer,
    CurrencySerializer,
    EntityDetailsSerializer,
    EntityEditAccessSerializer,
    EntityEditSerializer,
    EntitySerializer,
    TransferDetailsSerializer,
    TransferSerializer,
)
from tsosi.app_settings import app_settings
from tsosi.data.entity_edit import apply_entity_edit
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Analytic, Currency, Entity, EntityEditAccess, Transfer

IMAGE_MAX_SIZE = 2 * 1024 * 1024


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

    def get_edit_access(
        self, request: Request
    ) -> tuple[EntityEditAccess, Entity]:
        """
        Return the edit access matching the key given in the request's
        `Authorization: Bearer <key>` header, and the entity of the URL.
        """
        auth = request.headers.get("Authorization", "")
        key = auth.removeprefix("Bearer ").strip()
        if not auth.startswith("Bearer ") or not key:
            raise PermissionDenied("Missing edit access key.")
        try:
            entity = Entity.objects.get_by_any_id(
                self.kwargs[self.lookup_url_kwarg or self.lookup_field]
            ).sucessor_or_self()
        except Entity.DoesNotExist:
            raise Http404
        try:
            access = EntityEditAccess.objects.get_by_key(key)
        except EntityEditAccess.DoesNotExist:
            raise PermissionDenied("Invalid or expired edit access key.")
        if not access.grants(entity) or not entity.is_active:
            raise PermissionDenied("Invalid or expired edit access key.")
        return access, entity

    @staticmethod
    def validate_image(request: Request, field: str):
        """Return the valid image uploaded in the given field, if any."""
        image = request.FILES.get(field)
        if image is None:
            return None
        if image.size > IMAGE_MAX_SIZE:
            raise ValidationError({field: "The image must be under 2 MB."})
        try:
            forms.ImageField().clean(image)
        except DjangoValidationError as e:
            raise ValidationError({field: e.messages})
        image.seek(0)
        return image

    @action(
        detail=True,
        methods=["get", "patch"],
        parser_classes=[JSONParser, MultiPartParser],
    )
    def edit(self, request: Request, *args, **kwargs):
        """
        GET:    Check the validity of the edit access key.
        PATCH:  Edit the entity. The body is either the JSON edit data, or
                a multipart form with the JSON edit data in the `data` field
                and the optional image files in the `logo` & `icon` fields.
        """
        access, entity = self.get_edit_access(request)
        if request.method == "GET":
            return Response(EntityEditAccessSerializer(access).data)

        logo, icon = None, None
        if request.content_type.startswith("multipart/"):
            try:
                data = json.loads(request.data.get("data") or "{}")
            except json.JSONDecodeError:
                raise ValidationError({"data": "Invalid JSON."})
            logo = self.validate_image(request, "logo")
            icon = self.validate_image(request, "icon")
        else:
            data = request.data

        serializer = EntityEditSerializer(
            data=data, context={"entity": entity}
        )
        serializer.is_valid(raise_exception=True)
        apply_entity_edit(
            entity, access, serializer.validated_data, logo=logo, icon=icon
        )

        entity = self.get_queryset().get(id=entity.id)
        return Response(
            EntityDetailsSerializer(entity, context={"request": request}).data
        )


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
