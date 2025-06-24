from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import empty_db


class Command(BaseCommand):
    help = "Empty TSOSI database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--incl_currency",
            action="store_true",
            help="If passed, also empty currency related tables.",
        )

    def handle(self, *args, **options):
        empty_db(incl_currency=options["incl_currency"])
