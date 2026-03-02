import os
import sys
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

from tsosi.app_settings import app_settings
from tsosi.data.preparation.cleaning_utils import clean_cell_value


def main() -> None:
    raw_folder = Path(BASE_DIR) / "_no_git/data/raw/rennes"
    raw_path = str(
        raw_folder / f"2026--TSOSI-data-schema-institution-rennes.xlsx"
    )
    export_path = str(raw_folder / f"2026-02-27_rennes_full.xlsx")
    df = pd.read_excel(raw_path)

    mapping = {
        "infrastructure/name": "recipient/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "date_received": "date_received",
        "contract/date_start": "date_start",
        "contract/date_end": "date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    # Clean string values
    df.loc[:, ["recipient/name", "intermediary/name"]] = df[
        ["recipient/name", "intermediary/name"]
    ].map(clean_cell_value)

    # Remove Sparc europe rows
    df = df[~df["recipient/name"].str.contains("SPARC Europe", na=False)]

    # Add institution identifiers
    infrastructure_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/rennes"
        / "infrastructure_lookup.csv"
    )
    infrastructure_lookup = pd.read_csv(
        infrastructure_path, delimiter=";", dtype=str
    )
    df = df.merge(
        infrastructure_lookup,
        how="left",
    )

    # df[
    #     df["recipient/ror_id"].isna()
    #     & df["recipient/wikidata_id"].isna()
    #     & df["recipient/custom_id"].isna()
    # ]["recipient/name"].unique()

    consortium_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/rennes"
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(
        consortium_lookup_path, delimiter=";", dtype=str
    )
    df = df.merge(
        consortium_lookup,
        how="left",
    )

    # df[
    #     (df["intermediary/name"].notna())
    #     & df["intermediary/ror_id"].isna()
    #     & df["intermediary/wikidata_id"].isna()
    # ]

    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
