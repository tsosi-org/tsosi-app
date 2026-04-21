import os
import sys
from datetime import date
from pathlib import Path

import django
import pandas as pd
from IPython.display import display
from openpyxl import load_workbook

# Add the parent directory to the system path and setup django
BASE_DIR = str(Path(os.getcwd()).resolve())

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_site.settings")

django.setup()

from tsosi.data.ingestion.core import MAX_AGENTS_PER_TRANSFER
from tsosi.data.preparation.cleaning_utils import clean_cell_value

NAME = "mersenne"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / f"2026_04_13_TSOSI.xlsx")
    df = pd.read_excel(raw_path)

    mapping = {
        "institution/name": "emitter/name",
        "institution/ror_id": "emitter/ror_id",
        "institution/wikidata_id": "emitter/wikidata_id",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "hide_amount": "hide_amount",
        "date_invoice": "date_invoice",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    df.loc[:, ["emitter/name", "intermediary/name"]] = df[
        ["emitter/name", "intermediary/name"]
    ].map(clean_cell_value)

    # Add institution identifiers
    df["emitter/sub"] = ""
    df.loc[df["emitter/name"].str.contains("GATES"), "emitter/sub"] = "GATES"
    df.loc[df["emitter/name"] == "Math in France", "emitter/wikidata_id"] = (
        "Q21619045"
    )
    df.loc[
        df["emitter/name"].str.contains("DDOR"),
        ["emitter/ror_id", "emitter/sub"],
    ] = ("02feahw73", "DDOR")

    df = df[~df["amount"].isna()]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
