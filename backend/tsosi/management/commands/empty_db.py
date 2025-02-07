from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import empty_db


class Command(BaseCommand):
    help = "Ingest all data files in the INGEST directory."

    def handle(self, *args, **options):
        empty_db()
