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
    def REDIS_PORT(self) -> str:
        return self._setting("REDIS_PORT", mandatory=True)

    @property
    def REDIS_DB(self) -> str:
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
            "password": The name of the scipost user with elevated rights,
            "client_id": The ID of the OAuth2 application created to retrieve an auth token,
            "client_secret": Tee secret of the OAuth2 application created to retrieve an auth token
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


app_settings = AppSettings()
