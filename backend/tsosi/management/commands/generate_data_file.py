from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser
from tsosi.data.preparation.default.default import get_config


class Command(BaseCommand):
    help = "Generate data file for a given directory."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "file_path",
            type=str,
            help="directory path",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        date_data = date.fromisoformat(file_path.stem[:10])
        sheet_name = 0

        config = get_config(file_path.as_posix(), sheet_name, date_data)
        config.generate_data_file()
