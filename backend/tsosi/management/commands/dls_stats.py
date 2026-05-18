from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import DataLoadSource


class Command(BaseCommand):
    help = "Get stats about a data load source."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "dls",
            help="DataLoadSource id",
        )

    def handle(self, *args, **options):
        print(DataLoadSource.objects.get(id=options["dls"]).stats())
