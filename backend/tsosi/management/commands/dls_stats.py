from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import DataLoadSource, Entity


class Command(BaseCommand):
    help = "Get stats about a data load source."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "entity_id",
            help="DataLoadSource id",
        )

    def handle(self, *args, **options):
        entity = Entity.objects.get_by_any_id(options["entity_id"])
        print(DataLoadSource.objects.get(entity=entity).stats())
