from django.conf import settings


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


app_settings = AppSettings()
