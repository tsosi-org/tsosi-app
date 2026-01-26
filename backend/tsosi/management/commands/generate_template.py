from datetime import date
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from tsosi.api.viewsets import TransferViewSet
from tsosi.data.ingestion.transfer_matching import format_date
from tsosi.models import Entity, Transfer


def generate_template_file(entity_id: str) -> None:
    values = {entity_id} | set(
        Entity.objects.get(id=entity_id)
        .get_all_children()
        .values_list("id", flat=True)
    )
    condition = (
        Q(emitter_id__in=values)
        | Q(recipient_id__in=values)
        | Q(agent_id__in=values)
    ) & Q(merged_into__isnull=True)
    transfers = Transfer.objects.filter(condition).select_related(
        "emitter", "recipient", "agent", "currency"
    )
    df = pd.DataFrame(
        list(
            transfers.values(
                "emitter__name",
                "agent__name",
                "recipient__name",
                "amount",
                "currency__id",
                "date_invoice",
                "date_payment_emitter",
                "date_payment_recipient",
                "date_start",
                "date_end",
                "description",
            )
        )
    )
    for field in [
        "date_invoice",
        "date_payment_emitter",
        "date_payment_recipient",
        "date_start",
        "date_end",
    ]:
        df[field] = df[field].apply(format_date)
    output_path = "template_data_file.xlsx"
    df.to_excel(output_path, index=False)
    print(f"Template data file generated at: {output_path}")


class Command(BaseCommand):
    help = "Generate template data file for a given entity."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "id",
            type=str,
            help="any entity id",
        )

    def handle(self, *args, **options):
        generate_template_file(options["id"])
