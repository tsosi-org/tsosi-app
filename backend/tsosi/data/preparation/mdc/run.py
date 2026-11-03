import os
import sys
from pathlib import Path

import django
import pandas as pd

# Add the parent directory to the system path and setup django
BASE_DIR = str(Path(os.getcwd()).resolve())

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_site.settings")

django.setup()

from tsosi.data.preparation.cleaning_utils import clean_cell_value

NAME = "mdc"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME
LOOKUP_FOLDER = Path(BASE_DIR) / "tsosi/data/preparation" / NAME
# Date DataCite sent the file
DATE_DATA = "2026-10-21"


def main() -> None:
    # Spreadsheet of the donations received by DataCite and Make Data Count.
    # The "DataCite" sheet has no fees, only donations: not ingested yet.
    raw_path = str(RAW_FOLDER / "Donations Received.xlsx")
    df = pd.read_excel(raw_path, sheet_name="MDC")
    mapping = {
        "Organizations": "emitter/name",
        "Country": "emitter/country",
        "Intermediary": "agent/name",
        "Amount": "amount",
        # Year the payment was received
        "Year": "date_received",
    }
    # Also drops the side totals (unnamed column)
    df = df.rename(columns=mapping)[mapping.values()]
    df = df.map(clean_cell_value)
    df["date_received"] = df["date_received"].astype(int).astype(str)

    # Add identifiers
    for lookup in ["institution", "intermediary"]:
        lookup_df = pd.read_csv(
            LOOKUP_FOLDER / f"{lookup}_lookup.csv", delimiter=";", dtype=str
        )
        df = df.merge(lookup_df, how="left")

    missing = df["emitter/ror_id"].isna()
    if missing.any():
        print("Emitters without ROR ID:")
        print(df.loc[missing, "emitter/name"].unique())
    missing = df["agent/name"].notna() & df["agent/ror_id"].isna()
    if missing.any():
        print("Intermediaries without ROR ID:")
        print(df.loc[missing, "agent/name"].unique())

    export_path = str(RAW_FOLDER / f"{DATE_DATA}_{NAME}_full.xlsx")
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
