from django.core.management.base import BaseCommand

from tsosi.data.blog import fetch_blog


class Command(BaseCommand):
    help = (
        "Download the latest blog package and extract it to the frontend "
        "public directory. This will overwrite existing blog content. "
    )

    def handle(self, *args, **options):
        fetch_blog()
        self.stdout.write(
            self.style.SUCCESS("Blog content updated successfully.")
        )
