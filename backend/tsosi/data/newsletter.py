"""
Subscription to the newsletter
"""

import logging
from enum import StrEnum

from tsosi.data.sympa import SympaClient

logger = logging.getLogger(__name__)


class NewsletterAction(StrEnum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


def apply(email: str, action: NewsletterAction) -> None:
    """
    Apply the (un)subscription of the e-mail to the mailing list. Raises
    `SympaError` and `requests.RequestException` when the list couldn't be
    updated. Applying it twice is harmless.
    """
    client = SympaClient()
    client.login()
    if action == NewsletterAction.SUBSCRIBE:
        client.add(email)
    else:
        client.delete(email)
    logger.info(f"Newsletter {action} applied for {email}")
