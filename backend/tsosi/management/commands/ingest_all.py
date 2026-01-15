from django.core.management.base import BaseCommand, CommandParser
from tsosi.tasks import ingest_all


class Command(BaseCommand):
    help = "Ingest all data files in the INGEST directory."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "dir_path",
            nargs="?",
            type=str,
            help="Data dir full path",
        )

    def handle(self, *args, **options):
        ingest_all(options["dir_path"])
        return
