from urllib.parse import urlparse

from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle
from tsosi.app_settings import app_settings


def is_origin_whitelist(origin: str | None) -> bool:
    """Whether the given origin URL is allowed."""
    if origin is None or origin == "":
        return False
    url = urlparse(origin)
    return url.hostname in settings.ALLOWED_HOSTS


def is_IP_allowed(ip_address: str | None) -> bool:
    """Whether the IP address starts with withelisted IPV4 ranges."""
    if ip_address is None:
        return False
    # Only check IPV4 address string
    if len(ip_address.split(".")) != 4:
        return False
    for ip_start in app_settings.API_WHITELIST_IPS:
        if ip_address.startswith(ip_start):
            return True
    return False


class TsosiThrottle(AnonRateThrottle):
    """
    Custom API throttler for all API requests.
    Throttling is active by default except one of the following condition
    is met:
        - The request is originated by TSOSI front-end application.
        - The requester IP is within a custom list of IP addresses.
    """

    rate = app_settings.API_RATE

    def get_cache_key(self, request: Request, view):
        origin = request.META.get("HTTP_ORIGIN") or request.META.get(
            "HTTP_REFERER"
        )
        if is_origin_whitelist(origin):
            return None

        if is_IP_allowed(self.get_ident(request)):
            return None

        return super().get_cache_key(request, view)
