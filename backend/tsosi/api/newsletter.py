"""
Newsletter subscription endpoints (`tsosi.data.newsletter`).
"""

import logging

import requests
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tsosi.api.throttle import NewsletterRequestThrottle
from tsosi.data.newsletter import NewsletterAction, apply
from tsosi.data.sympa import SympaError

logger = logging.getLogger(__name__)

MAX_EMAIL_LENGTH = 254


class NewsletterRequestView(APIView):
    """
    (Un)subscribe the given e-mail. The answer is the same whether the address
    was already subscribed or not, not to disclose the subscribers.
    """

    authentication_classes = []
    permission_classes = []
    throttle_classes = [NewsletterRequestThrottle]
    action: NewsletterAction = NewsletterAction.SUBSCRIBE

    def post(self, request: Request) -> Response:
        email = request.data.get("email")
        if not isinstance(email, str) or len(email) > MAX_EMAIL_LENGTH:
            return invalid_email()
        email = email.strip()
        try:
            EmailValidator()(email)
        except ValidationError:
            return invalid_email()

        try:
            apply(email, self.action)
        except (SympaError, requests.RequestException):
            logger.exception("Error while updating the newsletter's list.")
            return Response(
                {"error": "The request failed, please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"action": self.action, "email": email})


def invalid_email() -> Response:
    return Response(
        {"error": "Invalid e-mail address."},
        status=status.HTTP_400_BAD_REQUEST,
    )
