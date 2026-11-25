import pandas as pd
from django.core.management.base import BaseCommand, CommandError, CommandParser

from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Entity

TSOSI_TYPES = [
    "infrastructure",
    "lib_consort",
    "funder",
    "company",
    "rpo",
    "other",
]


class Command(BaseCommand):
    help = "Fill tsosi types (see https://github.com/tsosi-org/type-entities)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "filepath",
            help="tsosi-entity-types.csv (tsosi_id, tsosi_type, ...)",
        )

    def handle(self, *args, **options):
        fill_types(options["filepath"])


def fill_types(filepath: str) -> None:
    df = pd.read_csv(filepath, dtype=str).fillna("")
    unknown = sorted(set(df["tsosi_type"]) - set(TSOSI_TYPES))
    if unknown:
        raise CommandError(
            f"Unknown tsosi_type {unknown}, expected {TSOSI_TYPES}"
        )

    # Entities are matched on their TSOSI id
    for tsosi_type, rows in df.groupby("tsosi_type"):
        count = Entity.objects.filter(
            identifiers__registry_id=REGISTRY_TSOSI,
            identifiers__value__in=rows["tsosi_id"].tolist(),
        ).update(tsosi_type=tsosi_type)
        print(f"Updated {count} entities to tsosi_type '{tsosi_type}'")

    # Entities not typed yet (still to review) are marked "other"
    count = Entity.objects.filter(tsosi_type__isnull=True).update(
        tsosi_type="other"
    )
    print(f"Updated {count} entities without type to tsosi_type 'other'")
