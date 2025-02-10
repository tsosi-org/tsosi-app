from django.core.management.base import BaseCommand, CommandParser
from tsosi.tasks import ingest_test


class Command(BaseCommand):
    help = "Ingest all data files in the tsosi/data/fixtures/prepared_files directory."

    def handle(self, *args, **options):
        ingest_test()
