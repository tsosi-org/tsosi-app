from django.core.management.base import BaseCommand

from tsosi.app_settings import app_settings
from tsosi.data.github_api import GitHubClient
from tsosi.data.newsletters import refresh_newsletters


class Command(BaseCommand):
    help = (
        "Store the new and changed newsletters of the newsletter repository. "
        "Also run hourly by the `refresh_news` task."
    )

    def handle(self, *args, **options):
        updated = refresh_newsletters(GitHubClient(app_settings.NEWS_BOARD))
        self.stdout.write(
            self.style.SUCCESS(f"{updated} newsletters stored or updated.")
        )
