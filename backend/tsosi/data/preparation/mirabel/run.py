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

NAME = "mirabel"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(
        RAW_FOLDER / f"2026--TSOSI-data-schema-infra-mirabel_20200414.xlsx"
    )
    df = pd.read_excel(raw_path)

    mapping = {
        "institution/name": "emitter/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_sent": "date_sent",
        "date_received": "date_received",
        "contract/date_start": "contract/date_start",
        "contract/date_end": "contract/date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    df.loc[:, ["emitter/name", "intermediary/name"]] = df[
        ["emitter/name", "intermediary/name"]
    ].map(clean_cell_value)

    # Add infra identifiers
    institution_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "institution_lookup.csv"
    )
    institution_lookup = pd.read_csv(institution_path, delimiter=";", dtype=str)
    df = df.merge(
        institution_lookup,
        how="left",
    )
    # df = df[~(df["emitter/ror_id"].isna() & df["emitter/wikidata_id"].isna())]

    consortium_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(
        consortium_lookup_path, delimiter=";", dtype=str
    )
    consortium_lookup["intermediary/name"] = consortium_lookup[
        "intermediary/name"
    ].map(clean_cell_value)
    df = df.merge(
        consortium_lookup,
        how="left",
    )
    # df[~df["intermediary/name"].isna() & (df["emitter/ror_id"].isna() & df["emitter/wikidata_id"].isna())]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
