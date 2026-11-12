from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

TSOSI_DIR = Path(__file__).resolve().parent


class AppSettings:
    """Wrapper for Django settings related to this application."""

    prefix = "TSOSI_"

    def _setting(self, name: str, default=None, mandatory=False):
        """
        Gets the queried setting with the app prefix.
        :param name:    The name of the setting.
        :param default: Fallback if the setting is not defined.
        """
        full_name = self.prefix + name
        if mandatory:
            try:
                getattr(settings, full_name)
            except AttributeError:
                raise Exception(
                    f"The mandatory app setting {full_name} is missing."
                )
        return getattr(settings, full_name, default)

    @property
    def API_BYPASS_PAGINATION_ALLOWED_ORIGINS(self) -> list[str]:
        """
        The list of origins allowed to bypass API pagination.
        """
        return self._setting("BYPASS_PAGINATION_ALLOWED_ORIGINS", ["*"])

    @property
    def REDIS_HOST(self) -> str:
        return self._setting("REDIS_HOST", mandatory=True)

    @property
    def REDIS_PORT(self) -> int:
        return self._setting("REDIS_PORT", mandatory=True)

    @property
    def REDIS_DB(self) -> int:
        return self._setting("REDIS_DB", mandatory=True)

    @property
    def TSOSI_APP_DIR(self) -> Path:
        return TSOSI_DIR

    @property
    def TSOSI_APP_DATA_DIR(self) -> Path:
        return TSOSI_DIR / "data"

    @property
    def TO_INGEST_DIR(self) -> Path:
        obj = self._setting("TO_INGEST_DIR", mandatory=True)
        return obj if isinstance(obj, Path) else Path(obj)

    @property
    def DATA_EXPORT_FOLDER(self) -> Path:
        obj = self._setting("DATA_EXPORT_FOLDER", mandatory=True)
        return obj if isinstance(obj, Path) else Path(obj)

    @property
    def TRIGGER_JOBS(self) -> bool:
        return self._setting("TRIGGER_JOBS", default=False)

    @property
    def SCIPOST_AUTH(self) -> dict | None:
        """
        The authentication credentials used to fetch SciPost protected data.
        The dictionnary requires the following data:
        ```
        {
            "username": The name of the scipost user with elevated rights,
            "password": The password of the scipost user with elevated rights,
            "client_id": The ID of the OAuth2 application created to retrieve an auth token,
            "client_secret": The secret of the OAuth2 application created to retrieve an auth token
        }
        ```
        """
        val = self._setting("SCIPOST_AUTH", mandatory=True)
        if not isinstance(val, dict):
            raise ImproperlyConfigured(
                f"Wrong data type for setting `SCIPOST_AUTH`: {val}"
            )
        relevant_keys = ["username", "password", "client_id", "client_secret"]
        for key in relevant_keys:
            if val.get(key) is None:
                raise ImproperlyConfigured(
                    f"Missing value for `SCIPOST_AUTH` required key: {key}"
                )
        return val

    @property
    def NEWS_BOARD(self) -> dict | None:
        """
        The GitHub project board where the TSOSI team picks the news of the
        home page (see `tsosi.data.news`). `None` disables the news refresh.
        ```
        {
            "owner": The organization owning the project, ex: "tsosi-org",
            "project_number": The project number, in its URL,
            # Authentication, either with a GitHub App installed on the
            # organization:
            "app_id": The ID of the GitHub App,
            "installation_id": The ID of its installation on the organization,
            "private_key": The private key of the GitHub App (PEM),
            # or with a token:
            "token": A GitHub token,
            # Optional
            "linkedin_repos": Repositories whose issues with a LinkedIn URL
                are proposed, default ["tsosi-org/newsletter"],
            "newsletter_repo": default "tsosi-org/newsletter",
            "issue_repo": Repository of the issues created for the blog posts
                and newsletters, default "tsosi-org/newsletter",
            "candidates_status": default "Candidates",
            "shown_status": default "Live",
            "max_items": Maximum number of news shown, default 3,
            "propose_days": Only news published in the last `propose_days`
                days are proposed, default 90,
        }
        ```
        The App or token needs the organization permission "Projects: read
        and write" and the repository permissions "Contents: read" and
        "Issues: read and write" on the newsletter and LinkedIn repositories.
        """
        val = self._setting("NEWS_BOARD")
        if val is None:
            return None
        if not isinstance(val, dict):
            raise ImproperlyConfigured(
                f"Wrong data type for setting `NEWS_BOARD`: {type(val)}"
            )
        for key in ["owner", "project_number"]:
            if val.get(key) is None:
                raise ImproperlyConfigured(
                    f"Missing value for `NEWS_BOARD` required key: {key}"
                )
        has_app = all(
            val.get(k) for k in ["app_id", "installation_id", "private_key"]
        )
        if not has_app and not val.get("token"):
            raise ImproperlyConfigured(
                "`NEWS_BOARD` requires either a `token` or the `app_id`, "
                "`installation_id` and `private_key` of a GitHub App."
            )
        return {
            "linkedin_repos": ["tsosi-org/newsletter"],
            "newsletter_repo": "tsosi-org/newsletter",
            "issue_repo": "tsosi-org/newsletter",
            "candidates_status": "Candidates",
            "shown_status": "Live",
            "max_items": 3,
            "propose_days": 90,
            **val,
        }

    @property
    def IDENTIFIER_FETCH_RETRY(self) -> int:
        """
        The maximum number of attempts for fetching an individual identifier
        record when it repeatedly failed over a given time window.
        """
        return self._setting("IDENTIFIER_FETCH_RETRY", 3)

    @property
    def IDENTIFIER_FETCH_DAYS(self) -> int:
        """The above-mentioned time window, in days."""
        return self._setting("IDENTIFIER_FETCH_DAYS", 1)

    @property
    def IDENTIFIER_REFRESH_DAYS(self) -> int:
        """The number of days before refreshing existing identifier records."""
        return self._setting("IDENTIFIER_REFRESH_DAYS", 1)

    @property
    def WIKI_FETCH_RETRY(self) -> int:
        """
        The maximum number of attempts for fetching a wiki-related resource
        when it repeatedly failed over a given time window
        """
        return self._setting("WIKI_FETCH_RETRY", 3)

    @property
    def WIKI_FETCH_DAYS(self) -> int:
        """The above-mentioned time window, in days."""
        return self._setting("WIKI_FETCH_DAYS", 1)

    @property
    def WIKI_REFRESH_DAYS(self) -> int:
        """The number of days before refreshing existing wiki-related data."""
        return self._setting("WIKI_REFRESH_DAYS", 7)

    @property
    def API_WHITELIST_IPS(self) -> list[str]:
        """
        A list of IP prefix strings that should be whitelisted from rate
        limiting.
        This is a heuristic to whitelist whole subnet masks, working for UGA
        because the known masks span exactly either 3 or 4 bytes.
        """
        return self._setting("API_WHITELIST_IPS", [])

    @property
    def FRONTEND_CUSTOM_HEADER(self) -> str:
        """
        Name of the custom HTTP header that should be sent by TSOSI frontend.
        It's used to bypass rate limiting (easily spoofable).
        """
        return self._setting("FRONTEND_CUSTOM_HEADER")

    @property
    def FRONTEND_CUSTOM_HEADER_VALUES(self) -> list[str]:
        """
        Allowed values for the custom HTTP header that will indeed bypass
        the default rate limiting.
        """
        return self._setting("FRONTEND_CUSTOM_HEADER_VALUES", ["tsosi-app"])

    @property
    def PUBLIC_RELPATH(self) -> str:
        """
        Relative path to the public frontend directory.
        """
        return self._setting("PUBLIC_RELPATH")

    @property
    def API_RATE(self) -> str:
        """
        The rate limit for the API, defaults to 10 per minute.
        """
        return self._setting("API_RATE", "100/m")

    @property
    def FRONTEND_URL(self) -> str:
        """
        Base URL of the frontend application, used to build the entity edit
        links.
        """
        return self._setting("FRONTEND_URL", "https://tsosi.org").rstrip("/")

    @property
    def EDIT_ACCESS_DAYS(self) -> int:
        """Default validity duration, in days, of entity edit accesses."""
        return self._setting("EDIT_ACCESS_DAYS", 7)

    @property
    def NEWSLETTER_SYMPA_URL(self) -> str:
        """Base URL of the Sympa instance hosting the newsletter's list."""
        return self._setting(
            "NEWSLETTER_SYMPA_URL",
            "https://listes.univ-grenoble-alpes.fr/sympa",
        ).rstrip("/")

    @property
    def NEWSLETTER_SYMPA_LIST(self) -> str:
        """Name of the newsletter's Sympa mailing list."""
        return self._setting("NEWSLETTER_SYMPA_LIST", "tsosi")

    @property
    def NEWSLETTER_SYMPA_OWNER(self) -> dict:
        """
        The credentials of an owner of the newsletter's Sympa list, used to
        add and remove subscribers: `{"email": ..., "password": ...}`, with
        the Sympa local password of that address.
        """
        val = self._setting("NEWSLETTER_SYMPA_OWNER", mandatory=True)
        if not isinstance(val, dict) or not all(
            val.get(key) for key in ["email", "password"]
        ):
            raise ImproperlyConfigured(
                "`TSOSI_NEWSLETTER_SYMPA_OWNER` requires an `email` and a "
                "`password`."
            )
        return val

    @property
    def NEWSLETTER_REQUEST_RATE(self) -> str:
        """
        Rate limit, per IP address, of the newsletter subscription and
        unsubscription requests, which call Sympa.
        """
        return self._setting("NEWSLETTER_REQUEST_RATE", "5/h")

    @property
    def ERROR_OUTPUT_FOLDER(self) -> str:
        """
        A directory outside of git management for temporary files.
        """
        return self._setting("ERROR_OUTPUT_FOLDER", "/tmp/tsosi/errors")


app_settings = AppSettings()
