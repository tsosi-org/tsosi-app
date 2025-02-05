from django.core.management.base import BaseCommand, CommandParser
from tsosi.tasks import ingest_data_file


class Command(BaseCommand):
    help = "Ingest the given data file."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "file_path",
            type=str,
            help="Data file full path",
        )

    def handle(self, *args, **options):
        ingest_data_file(options["file_path"])
