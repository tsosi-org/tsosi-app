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
    raw_path = str(
        RAW_FOLDER / "Overview_SCOSS_FundingCycles_CSAL_TSOSI_fixed.xlsx"
    )
    df = pd.read_excel(raw_path)
    mapping = {
        "institution/name": "emitter/name",
        "institution/ror_id": "emitter/ror_id",
        "infrastructure/name": "recipient/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_sent": "date_sent",
        "date_received": "date_received",
        "contract/date_start": "date_start",
        "contract/date_end": "date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df.map(clean_cell_value)

    # Fixes from Make Data Count's data (sent by DataCite on 2026-10-21):
    # CERN pays 1,750 € a year and ETH Zurich paid its 3 years at once in 2025.
    is_mdc = df["recipient/name"] == "Make Data Count"
    is_cern = df["emitter/name"] == "European Organization for Nuclear Research"
    df.loc[is_mdc & is_cern, "amount"] = 1750
    is_eth = is_mdc & (df["emitter/name"] == "ETH Zurich")
    df = df.drop(df[is_eth & (df["date_invoice"] != 2025)].index)
    is_eth = is_eth[df.index]
    df.loc[is_eth, ["amount", "date_start", "date_end"]] = [10500, 2025, 2027]

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
