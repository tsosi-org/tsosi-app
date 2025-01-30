from pathlib import Path

from django.conf import settings

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
    def CELERY_BROKER(self) -> str:
        return self._setting("CELERY_BROKER", mandatory=True)

    @property
    def DATA_FOLDER_PATH(self) -> str:
        return self._setting("DATA_FOLDER_PATH", mandatory=True)

    @property
    def TSOSI_APP_DIR(self) -> Path:
        return TSOSI_DIR

    @property
    def TSOSI_APP_DATA_DIR(self) -> Path:
        return TSOSI_DIR / "data"

    @property
    def TSOSI_APP_TO_INGEST_DIR(self) -> Path:
        return TSOSI_DIR / "data" / "to_ingest"


app_settings = AppSettings()
