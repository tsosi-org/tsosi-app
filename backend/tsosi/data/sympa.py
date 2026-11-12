"""
Management of the newsletter's Sympa mailing list subscribers.
"""

import html
import logging
import re

import requests

from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.common import TSOSI_USER_AGENT

logger = logging.getLogger(__name__)

# Per call: a request makes up to 5 calls, within gunicorn's 30s timeout
TIMEOUT = 5
CSRF_RE = re.compile(r'name="csrftoken" value="([^"]+)"')
CONFIRM_FORM_RE = re.compile(
    r"<form[^>]*>(?:(?!</form>).)*?response_action_confirm.*?</form>", re.DOTALL
)
HIDDEN_INPUT_RE = re.compile(
    r'<input type="hidden" name="([^"]+)" value="([^"]*)"'
)
# Sympa's notifications, e.g. `<div class="alert-box alert radius">` for
# errors, `success` or `info` for notices.
ALERT_RE = re.compile(
    r'class="alert-box (\w+)[^"]*"[^>]*>(.*?)</div>', re.DOTALL | re.IGNORECASE
)
# Errors meaning that the list is already in the requested state, from
# Sympa's `report.tt2`
ALREADY_SUBSCRIBED = "is already subscriber"
NOT_SUBSCRIBED = "was not found in list"


class SympaError(Exception):
    pass


def alerts(page: str) -> list[tuple[str, str]]:
    """The (level, text) notifications shown in a Sympa page."""
    result = []
    for level, content in ALERT_RE.findall(page):
        text = html.unescape(re.sub(r"<[^>]+>", " ", content))
        result.append((level.lower(), " ".join(text.split())))
    return result


def errors(page: str) -> list[str]:
    return [text for level, text in alerts(page) if level == "alert"]


def csrf_token(page: str) -> str:
    match = CSRF_RE.search(page)
    if match is None:
        raise SympaError("No CSRF token in Sympa's page.")
    return match.group(1)


class SympaClient:
    """A web session of the newsletter list's owner."""

    def __init__(self):
        self.base_url = app_settings.NEWSLETTER_SYMPA_URL
        self.list = app_settings.NEWSLETTER_SYMPA_LIST
        self.session = requests.Session()
        # English pages, as the messages are parsed
        self.session.headers.update(
            {"Accept-Language": "en", "User-Agent": TSOSI_USER_AGENT}
        )

    def _get(self, path: str) -> str:
        res = self.session.get(f"{self.base_url}/{path}", timeout=TIMEOUT)
        res.raise_for_status()
        return res.text

    def _post(self, data: dict) -> str:
        res = self.session.post(self.base_url, data=data, timeout=TIMEOUT)
        res.raise_for_status()
        return res.text

    def login(self) -> None:
        owner = app_settings.NEWSLETTER_SYMPA_OWNER
        page = self._get("login")
        page = self._post(
            {
                "csrftoken": csrf_token(page),
                "action": "login",
                "email": owner["email"],
                "passwd": owner["password"],
                "action_login": "Login",
                "submit": "submit",
            }
        )
        if errors(page) or 'name="passwd"' in page:
            raise SympaError(
                f"The login of the list owner failed: {errors(page)}"
            )

    def _owner_action(self, action: str, email: str, ok_error: str) -> None:
        """
        Run a quiet `add` or `del` action on the given e-mail, from the list's
        review page, and confirm it.
        """
        page = self._get(f"review/{self.list}")
        data = {
            "csrftoken": csrf_token(page),
            "list": self.list,
            "previous_action": "review",
            "email": email,
            "quiet": "on",
            f"action_{action}": action,
        }
        page = self._post(data)
        form = CONFIRM_FORM_RE.search(page)
        if form is not None:
            confirm = dict(HIDDEN_INPUT_RE.findall(form.group(0)))
            confirm["quiet"] = "on"
            confirm["response_action_confirm"] = "Confirm"
            page = self._post(confirm)
            if CONFIRM_FORM_RE.search(page):
                raise SympaError(f"Sympa didn't accept the `{action}` action.")

        page_errors = [e for e in errors(page) if ok_error not in e]
        if page_errors:
            raise SympaError(f"Sympa's `{action}` failed: {page_errors}")

    def add(self, email: str) -> None:
        """Subscribe the e-mail to the list, if it isn't already."""
        self._owner_action("add", email, ALREADY_SUBSCRIBED)

    def delete(self, email: str) -> None:
        """Unsubscribe the e-mail from the list, if it's subscribed."""
        self._owner_action("del", email, NOT_SUBSCRIBED)
