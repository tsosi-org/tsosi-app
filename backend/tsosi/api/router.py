from rest_framework.routers import DefaultRouter


class OptionalSlashRouter(DefaultRouter):
    """
    A custom router class to make route's trailing slash as optionnal.
    """

    def __init__(self):
        super().__init__()
        self.trailing_slash = "/?"
