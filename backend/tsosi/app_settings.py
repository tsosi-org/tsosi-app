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
        return self._setting("FRONTEND_CUSTOM_HEADER", "X-Frontend-Origin")

    @property
    def FRONTEND_CUSTOM_HEADER_VALUES(self) -> list[str]:
        """
        Allowed values for the custom HTTP header that will indeed bypass
        the default rate limiting.
        """
        return self._setting("FRONTEND_CUSTOM_HEADER_VALUES", ["tsosi-app"])

    @property
    def API_RATE(self) -> str:
        """
        The rate limit for the API, defaults to 10 per minute.
        """
        return self._setting("API_RATE", "100/m")


app_settings = AppSettings()
