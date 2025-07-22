from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import empty_db


class Command(BaseCommand):
    help = "Empty TSOSI database. Default only empty the transfer table."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--full",
            action="store_true",
            help="If passed, empty all TSOSI tables.",
        )

    def handle(self, *args, **options):
        empty_db(full=options["full"])
