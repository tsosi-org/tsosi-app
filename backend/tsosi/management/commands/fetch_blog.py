#
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import empty_db

BLOG_PKG_URL = "https://github.com/tsosi-org/tsosi-org.github.io/releases/latest/download/public.tar"


class Command(BaseCommand):
    help = "Download the latest blog package and extract it to the frontend public directory. This will overwrite existing blog content."

    def handle(self, *args, **options):
        os.system(f"mkdir -p {settings.TSOSI_PUBLIC_RELPATH}/pages/blog")
        os.system(f"wget -q {BLOG_PKG_URL} -O /tmp/public.tar")
        os.system(
            f"tar -xf /tmp/public.tar -C {settings.TSOSI_PUBLIC_RELPATH}/pages/blog"
        )
        self.stdout.write(
            self.style.SUCCESS("Blog content updated successfully.")
        )
