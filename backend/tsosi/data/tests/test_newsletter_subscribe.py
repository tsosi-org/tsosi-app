from unittest.mock import MagicMock

import pytest
import requests
from django.core.cache.backends.locmem import LocMemCache
from rest_framework.test import APIClient

from tsosi.api.throttle import NewsletterRequestThrottle
from tsosi.data.newsletter import NewsletterAction
from tsosi.data.sympa import SympaClient, SympaError

SYMPA = "https://listes.univ-grenoble-alpes.fr/sympa"
EMAIL = "someone@example.org"

# Excerpts of Sympa's pages (templates of Sympa 6.2.80)
LOGIN_PAGE = """
<form action="/sympa" method="post">
<input type="hidden" name="csrftoken" value="token-login" />
<input type="text" name="email" id="email_login" size="28" value="" />
<input type="password" name="passwd" id="passwd" />
</form>
"""
LOGIN_ERROR_PAGE = (
    """<div class="alert-box alert radius"><p>Incorrect password</p></div>"""
    + LOGIN_PAGE
)
HOME_PAGE = """
<div  data-alert class="alert-box info radius">
    <p>last login from 1.2.3.4</p>
</div>
"""
REVIEW_PAGE = """
<form action="/sympa" method="POST">
<input type="hidden" name="csrftoken" value="token-review" />
<input type="hidden" name="action" value="add" />
</form>
"""
CONFIRM_PAGE = """
<form action="/sympa" method="POST" autocomplete="off"><input type="hidden" name="csrftoken" value="token-confirm" />
    <input type="hidden" name="email" value="someone@example.org" />
    <input type="hidden" name="action" value="add" />
    <input type="hidden" name="list" value="tsosi" />
    <input type="hidden" name="previous_action" value="review" />
    <input class="MainMenuLinks" type="submit"
           id="response_action_confirm" name="response_action_confirm"
           value="Confirm" />
</form>
"""
DONE_PAGE = """
<div  data-alert class="alert-box success radius">
    <i class="fa fa-check" aria-hidden="true"></i>
    <p>1 addresses have been added</p>
</div>
"""


def error_page(message: str) -> str:
    return f'<div class="alert-box alert radius"><p>{message}</p></div>'


def response(text: str) -> MagicMock:
    res = MagicMock(text=text)
    res.raise_for_status.return_value = None
    return res


@pytest.fixture(autouse=True)
def owner(settings):
    settings.TSOSI_NEWSLETTER_SYMPA_OWNER = {
        "email": "owner@example.org",
        "password": "secret",
    }


@pytest.fixture
def sympa(mocker):
    """The mocked HTTP session used to call Sympa, for a successful add."""
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = [response(LOGIN_PAGE), response(REVIEW_PAGE)]
    session.post.side_effect = [
        response(HOME_PAGE),
        response(CONFIRM_PAGE),
        response(DONE_PAGE),
    ]
    mocker.patch("tsosi.data.sympa.requests.Session", return_value=session)
    return session


@pytest.fixture(autouse=True)
def throttle_cache(monkeypatch):
    cache = LocMemCache("test-newsletter", {})
    cache.clear()
    monkeypatch.setattr(NewsletterRequestThrottle, "cache", cache)


@pytest.fixture
def mock_client(mocker) -> MagicMock:
    """The mocked Sympa client used by the API."""
    return mocker.patch("tsosi.data.newsletter.SympaClient").return_value


def sympa_client() -> SympaClient:
    client = SympaClient()
    client.login()
    return client


# Sympa client


def test_sympa_add(sympa):
    sympa_client().add(EMAIL)

    assert [c.args[0] for c in sympa.get.call_args_list] == [
        f"{SYMPA}/login",
        f"{SYMPA}/review/tsosi",
    ]
    login, add, confirm = [c.kwargs["data"] for c in sympa.post.call_args_list]
    assert login["csrftoken"] == "token-login"
    assert login["email"] == "owner@example.org"
    assert login["passwd"] == "secret"
    assert login["submit"] == "submit"
    assert add == {
        "csrftoken": "token-review",
        "list": "tsosi",
        "previous_action": "review",
        "email": EMAIL,
        "quiet": "on",
        "action_add": "add",
    }
    # Sympa's confirmation form is sent back, with its own token
    assert confirm["csrftoken"] == "token-confirm"
    assert confirm["action"] == "add"
    assert confirm["quiet"] == "on"
    assert confirm["email"] == EMAIL
    assert "response_action_confirm" in confirm


def test_sympa_delete(sympa):
    sympa_client().delete(EMAIL)
    _, delete, _ = [c.kwargs["data"] for c in sympa.post.call_args_list]
    assert delete["action_del"] == "del"
    assert delete["quiet"] == "on"


def test_sympa_login_error(sympa):
    sympa.post.side_effect = [response(LOGIN_ERROR_PAGE)]
    with pytest.raises(SympaError):
        sympa_client()


def last_page(sympa, page: str):
    """Sympa answers the confirmed action with the given page."""
    sympa.post.side_effect = [
        response(HOME_PAGE),
        response(CONFIRM_PAGE),
        response(page),
    ]


@pytest.mark.parametrize(
    "action, page",
    [
        (
            "add",
            error_page(f"The User '{EMAIL}' is already subscriber of list"),
        ),
        ("delete", error_page(f"E-mail address {EMAIL} was not found in list")),
    ],
)
def test_sympa_already_done(sympa, action, page):
    last_page(sympa, page)
    getattr(sympa_client(), action)(EMAIL)


@pytest.mark.parametrize(
    "page",
    [
        error_page("You are not allowed to perform this action"),
        # The confirmation isn't accepted
        CONFIRM_PAGE,
    ],
)
def test_sympa_errors(sympa, page):
    last_page(sympa, page)
    with pytest.raises(SympaError):
        sympa_client().add(EMAIL)


# API


@pytest.mark.parametrize(
    "action", [NewsletterAction.SUBSCRIBE, NewsletterAction.UNSUBSCRIBE]
)
def test_request_view(action, mock_client):
    add, remove = mock_client.add, mock_client.delete
    res = APIClient().post(f"/api/newsletter/{action}", {"email": f" {EMAIL} "})

    assert res.status_code == 200
    assert res.json() == {"action": action, "email": EMAIL}
    called, not_called = (
        (add, remove) if action == NewsletterAction.SUBSCRIBE else (remove, add)
    )
    called.assert_called_once_with(EMAIL)
    not_called.assert_not_called()


@pytest.mark.parametrize(
    "data", [{}, {"email": "not-an-email"}, {"email": "a@b.c" * 100}]
)
def test_request_view_invalid_email(data, mock_client):
    res = APIClient().post("/api/newsletter/subscribe", data, format="json")
    assert res.status_code == 400
    mock_client.add.assert_not_called()
    mock_client.delete.assert_not_called()


def test_request_view_throttle(settings, mock_client):
    settings.TSOSI_NEWSLETTER_REQUEST_RATE = "1/h"
    client = APIClient()
    # The frontend header doesn't bypass this rate limit
    headers = {"HTTP_X_FRONTEND_ORIGIN": "tsosi-app"}
    url = "/api/newsletter/subscribe"
    assert client.post(url, {"email": EMAIL}, **headers).status_code == 200
    assert client.post(url, {"email": EMAIL}, **headers).status_code == 429


@pytest.mark.parametrize(
    "error", [SympaError("failed"), requests.ConnectionError("down")]
)
def test_request_view_sympa_error(error, mock_client):
    mock_client.add.side_effect = error
    res = APIClient().post("/api/newsletter/subscribe", {"email": EMAIL})
    assert res.status_code == 502
