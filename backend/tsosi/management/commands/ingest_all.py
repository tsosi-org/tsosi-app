from django.core.management.base import BaseCommand, CommandParser
from tsosi.tasks import ingest_all


class Command(BaseCommand):
    help = "Ingest all data files in the INGEST directory."

    def handle(self, *args, **options):
        ingest_all()
