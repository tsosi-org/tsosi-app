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

NAME = "gottingen"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(
        RAW_FOLDER / f"TSOSI-data-schema-institution-goettingen_20260602.xlsx"
    )
    df = pd.read_excel(raw_path, dtype="str")

    mapping = {
        "infrastructure/name": "recipient/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_emitted": "date_emitted",
        "date_received": "date_received",
        "contract/date_start": "contract/date_start",
        "contract/date_end": "contract/date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df.map(clean_cell_value)

    # Add infra identifiers
    infrastructure_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "infrastructure_lookup.csv"
    )
    infrastructure_lookup = pd.read_csv(
        infrastructure_path, delimiter=";", dtype=str
    )
    df = df.merge(
        infrastructure_lookup,
        how="left",
    )
    mask = (
        df["recipient/ror_id"].isna()
        & df["recipient/wikidata_id"].isna()
        & df["recipient/custom_id"].isna()
    )
    df.loc[mask, "recipient/name"]
    df = df[~mask]

    consortium_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(
        consortium_lookup_path, delimiter=";", dtype=str
    )
    df = df.merge(
        consortium_lookup,
        how="left",
    )
    mask = df["intermediary/name"].notna() & (
        df["intermediary/ror_id"].isna()
        & df["intermediary/wikidata_id"].isna()
        & df["intermediary/custom_id"].isna()
    )
    df.loc[mask, "intermediary/name"]
    df = df[~mask]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
