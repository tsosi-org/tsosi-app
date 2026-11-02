"""Login by a single-use e-mail link, logout and the logged in user."""

import logging
import re
import threading
from collections.abc import Callable
from urllib.parse import quote

from django.contrib.auth import get_user_model, login, logout
from django.core.mail import send_mail
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from sesame.utils import get_token, get_user

from tsosi.api.hub.base import HubView, IsMemberOrStaff, get_membership
from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity, Membership

logger = logging.getLogger(__name__)


# Scope of the login tokens, so that no other sesame token logs in
LOGIN_SCOPE = "hub"
LOGIN_EMAIL_SUBJECT = "Your TSOSI Data Contribution Hub login link"
LOGIN_EMAIL_MESSAGE = """Hello,

Use the link below to log in to the TSOSI Data Contribution Hub.
It's valid for 15 minutes and can only be used once.

{link}

If you didn't ask for it, you can ignore this e-mail.

The TSOSI team
"""


def run_in_background(func: Callable, *args) -> None:
    """
    Run the function in a thread, so that the response time doesn't tell
    whether an e-mail was sent.
    """

    def run():
        try:
            func(*args)
        except Exception:
            logger.exception("Error while running a background function.")

    threading.Thread(target=run).start()


# The path of a Hub page: `/hub`, then segments like an organization's ID
HUB_PATH = re.compile(r"/hub(?:/[\w-]+)*/?", re.ASCII)
MAX_NEXT_LENGTH = 2000


def hub_next_path(next_path: str) -> str | None:
    """
    The Hub page to go to after the login, with its query and hash (e.g. a
    shared link to a filtered table), or None if it isn't a Hub page of the
    frontend: the login link can't redirect elsewhere. Same check as
    `hubNextPath` in the frontend.
    """
    if len(next_path) > MAX_NEXT_LENGTH:
        return None
    path = re.split(r"[?#]", next_path, maxsplit=1)[0]
    if not HUB_PATH.fullmatch(path) or path.rstrip("/") == "/hub/login":
        return None
    return next_path


def send_login_link(user, next_path: str = "") -> None:
    token = get_token(user, scope=LOGIN_SCOPE)
    link = f"{app_settings.FRONTEND_URL}/hub/login"
    safe_next = hub_next_path(next_path)
    if safe_next:
        link += f"?next={quote(safe_next, safe='/')}"
    link += f"#token={token}"
    run_in_background(
        send_mail,
        LOGIN_EMAIL_SUBJECT,
        LOGIN_EMAIL_MESSAGE.format(link=link),
        # Sent from DEFAULT_FROM_EMAIL
        None,
        [user.email],
    )


class LoginLinkThrottle(AnonRateThrottle):
    scope = "hub_login_link"
    rate = "10/hour"


class LoginLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # The Hub page to go back to: ignored if not one
    next = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False
    )


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField()


def tsosi_id(entity: Entity) -> str | None:
    identifier = entity.identifiers.filter(registry_id=REGISTRY_TSOSI).first()
    return identifier.value if identifier else None


def session_data(user) -> dict:
    """
    The logged in user: their organization, if any, with its TSOSI ID (that
    of its Hub's URL), and their rights.
    """
    membership = get_membership(user)
    organization = None
    if membership is not None:
        organization = {
            "id": membership.entity.id,
            "tsosi_id": tsosi_id(membership.entity),
            "name": membership.entity.name,
        }
    return {
        "email": user.email,
        "is_staff": user.is_staff,
        "organization": organization,
        "can_declare_supports": bool(
            membership and membership.can_declare_supports
        ),
    }


class LoginLinkView(HubView):
    """
    POST: send a login link to the e-mail, if it belongs to an active member.
    The response is the same either way.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginLinkThrottle]

    def post(self, request):
        serializer = LoginLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = (
            get_user_model()
            .objects.filter(
                email__iexact=serializer.validated_data["email"],
                is_active=True,
                memberships__in=Membership.objects.active(),
            )
            .first()
        )
        if user is not None:
            send_login_link(user, serializer.validated_data.get("next", ""))
        return Response(status=204)


class LoginView(HubView):
    """POST: log in with the token of a login link."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # The login below updates the last login date, which makes the token
        # single-use.
        user = get_user(
            serializer.validated_data["token"],
            scope=LOGIN_SCOPE,
            update_last_login=False,
        )
        membership = get_membership(user) if user else None
        if membership is None:
            raise ValidationError(
                {"token": "This login link is invalid or expired."}
            )
        login(request, user)
        return Response(session_data(user))


class LogoutView(HubView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=204)


class MeView(HubView):
    """
    GET: the logged in member and their organization, or the logged in
    TSOSI team member (Django admin session).
    """

    permission_classes = [IsMemberOrStaff]

    def get(self, request):
        return Response(session_data(request.user))
