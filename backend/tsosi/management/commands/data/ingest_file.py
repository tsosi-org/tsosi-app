from django.core.management.base import BaseCommand, CommandParser
from tsosi.data.ingestion import ingest_new_records
from tsosi.data.preparation.raw_data_config import get_input_config

from backend.tsosi.data.preparation.cleaning_utils import prepare_data


class Command(BaseCommand):
    help = "Ingest the data according to given file & config type."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("config", nargs=1, type=str)
        parser.add_argument(
            "file_abs_path",
            nargs=1,
            type=str,
            help="Absolute path to the data file",
        )
        parser.add_argument(
            "--sheet_name", type=str, help="Sheet name for XLSX inputs."
        )

    def handle(self, *args, **options):
        config = get_input_config(
            options["config"], options["file_abs_path"], options["--sheet_name"]
        )
        prepare_data(config)
        ingest_new_records(config.processed_data)
