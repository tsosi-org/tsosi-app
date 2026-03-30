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

NAME = "doaj"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def handle_funder_2025() -> pd.DataFrame:
    raw_path = str(
        RAW_FOLDER / f"0_raw/ARCHIEVED_2025_Funder_Report_2026-03-05.xlsx"
    )
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "Company": "emitter/name",
        "Country": "emitter/country",
        "Support end date": "contract/date_end",
        "Currency": "currency",
        "Invoiced amount 2025": "amount",
        # "Status": "",
        # "Forecast amount 2025": "",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df[df["amount"].notna() & (df["emitter/name"].notna())]
    df["contract/date_end"] = pd.to_datetime(
        df["contract/date_end"], errors="coerce"
    ).dt.date
    df["date_received"] = "2025"
    df["date_invoice"] = "2025"
    df["contract/date_start"] = "2025-01-01"
    return df


def handle_library_2025() -> pd.DataFrame:
    raw_path = str(
        RAW_FOLDER / f"0_raw/ARCHIEVED_2025_Library_Report_2026-03-05.xlsx"
    )
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "Company": "emitter/name",
        "Country": "emitter/country",
        "Currency": "currency",
        "Agent": "intermediary/name",
        "Invoiced amount 2025": "amount",
        "Fincial year of payment": "date_received",
        # ...
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df[df["amount"].notna()]
    df = df[df["intermediary/name"] != "Couperin"]
    df = df[df["date_received"].notna()]
    df["date_invoice"] = df["date_received"]
    return df


def handle_publisher_2025() -> pd.DataFrame:
    raw_path = str(
        RAW_FOLDER / f"0_raw/ARCHIEVED_2025_Publishers_Report_2026-03-05.xlsx"
    )
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "Company": "emitter/name",
        "Country": "emitter/country",
        "Currency": "currency",
        "Actual amount": "amount",
        "Invoice date": "date_invoice",
        "Financial year of payment": "date_received",
        # ...
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df[df["amount"].notna()]
    df["date_invoice"] = pd.to_datetime(
        df["date_invoice"], errors="coerce"
    ).dt.date
    return df


def main() -> None:
    df = pd.concat(
        [
            handle_funder_2025(),
            handle_library_2025(),
            handle_publisher_2025(),
        ],
        ignore_index=True,
    )
    df.loc[:, ["emitter/name", "intermediary/name"]] = df[
        ["emitter/name", "intermediary/name"]
    ].map(clean_cell_value)

    # Add institution identifiers
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

    # df[df["emitter/ror_id"].isna() & df["emitter/wikidata_id"].isna()][
    #     "emitter/name"
    # ].unique().tolist()

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

    # df[
    #     df["intermediary/ror_id"].isna() & df["intermediary/wikidata_id"].isna() & df["intermediary/name"].notna()
    # ]["intermediary/name"].unique().tolist()

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
