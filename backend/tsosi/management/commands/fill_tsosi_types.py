import pandas as pd
from django.core.management.base import BaseCommand, CommandParser
from tsosi.models import Entity


class Command(BaseCommand):
    help = "Fill tsosi types (see https://github.com/tsosi-org/type-entities)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "filepath",
            help="TSOSI-type-entities.csv",
        )

    def handle(self, *args, **options):
        fill_types(options["filepath"])


def fill_types(filepath: str) -> None:
    df = pd.read_csv(filepath)
    # Entities that have ror type company are marked "company"
    Entity.objects.filter(ror_types=["company"]).update(tsosi_type="company")
    # Entities that are recipients are marked "infrastructure"
    Entity.objects.filter(is_recipient=True, is_agent=False).update(
        tsosi_type="infrastructure"
    )
    # Entities manually tagged in the TSOSI-type-entities.csv file are marked accordingly based on their ror_id or wiki_id
    for tsosi_type in ["lib_consort", "funder"]:
        mask = df["tsosi_type"] == tsosi_type
        ror_mask = df["ror_id"].notnull()
        wiki_mask = df["wiki_id"].notnull()
        ror_ids = df.loc[ror_mask & mask, "ror_id"].tolist()
        wikidata_ids = df.loc[wiki_mask & mask, "wiki_id"].tolist()
        Entity.objects.filter(identifiers__value__in=ror_ids).update(
            tsosi_type=tsosi_type
        )
        Entity.objects.filter(identifiers__value__in=wikidata_ids).update(
            tsosi_type=tsosi_type
        )
    # Update all remaining to "other"
    Entity.objects.filter(tsosi_type__isnull=True).update(tsosi_type="other")
