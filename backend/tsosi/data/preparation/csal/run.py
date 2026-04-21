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

from tsosi.app_settings import app_settings
from tsosi.data.preparation.cleaning_utils import clean_cell_value

NAME = "csal"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / "Overview_SCOSS_FundingCycles_CSAL_TSOSI.xlsx")
    df = pd.read_excel(raw_path)
    mapping = {
        "institution/name": "emitter/name",
        "institution/ror_id": "emitter/ror_id",
        "infrastructure/name": "recipient/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_received": "date_received",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    df.loc[:, ["emitter/name", "recipient/name"]] = df[
        ["emitter/name", "recipient/name"]
    ].map(clean_cell_value)

    # Add infra identifiers
    infra_path = (
        Path(BASE_DIR) / "tsosi/data/preparation" / NAME / "infra_lookup.csv"
    )
    infra_lookup = pd.read_csv(infra_path, delimiter=";", dtype=str)
    df = df.merge(
        infra_lookup,
        how="left",
    )
    df[
        (
            df["recipient/ror_id"].isna()
            & df["recipient/wikidata_id"].isna()
            & df["recipient/custom_id"].isna()
        )
    ]
    df[(df["emitter/ror_id"].isna())]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
