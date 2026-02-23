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

FIRST_YEAR = 2017


def main() -> None:
    raw_folder = Path(BASE_DIR) / "_no_git/data/raw/opf"
    raw_path = str(
        raw_folder / f"Sherpa_Romeo - Open Policy Finder - SCOSS Funding.xlsx"
    )
    export_path = str(raw_folder / f"2026-02-19_opf_full.xlsx")

    df = pd.read_excel(raw_path)

    mapping = {
        "Funder Full Name": "emitter/name",
        "Funder Acronym": "agent/name",
        "Funder Country": "emitter/country",
        # "Funder Contact Name": "",
        # "Funder Contact Email": "",
        # "Total Committed by the Funder (in Euros)": "",
        # "Date of Funding Commitment": "",
        "Year 1 Amount Paid (in Euros)": "year_1_amount",
        "Year 1 Paid Date": "year_1_date_paid",
        "Year 2 Amount Paid (in Euros)": "year_2_amount",
        "Year 2 Paid Date": "year_2_date_paid",
        "Year 3 Amount Paid (in Euros)": "year_3_amount",
        "Year 3 Paid Date": "year_3_date_paid",
        # "3 Years Paid in Full?": "",
        # "Additional Comments": "",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    # Clean string values
    df.loc[:, ["emitter/name", "agent/name", "emitter/country"]] = df[
        ["emitter/name", "agent/name", "emitter/country"]
    ].map(clean_cell_value)

    s = df.melt(["emitter/name", "agent/name", "emitter/country"])
    s[["year", "type"]] = (
        s["variable"].str.split("^(year_[0-9])_(.*)$", expand=True).iloc[:, 1:3]
    )
    s = s.pivot(
        index=["emitter/name", "agent/name", "emitter/country", "year"],
        columns=["type"],
        values="value",
    ).reset_index()

    df = s.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df[df["amount"].notna() & (df["amount"] != 0) & (df["amount"] != "")]

    # Format date
    df["date_paid"] = pd.to_datetime(
        df["date_paid"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    for year in range(1, 4):
        mask = df["year"] == f"year_{year}"
        df.loc[mask, "date_invoice"] = str(FIRST_YEAR - 1 + year)

    # Add institution identifiers
    institution_lookup_path = (
        Path(BASE_DIR) / "tsosi/data/preparation/opf" / "institution_lookup.csv"
    )
    institution_lookup = pd.read_csv(
        institution_lookup_path, delimiter=";", dtype=str
    )
    df = df.merge(
        institution_lookup,
        how="left",
    )

    # Add intermediary identifiers
    intermediary_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/opf"
        / "intermediary_lookup.csv"
    )
    intermediary_lookup = pd.read_csv(
        intermediary_lookup_path, delimiter=";", dtype=str
    )
    df = df.merge(
        intermediary_lookup,
        how="left",
    )
    df.loc[df["agent/ror_id"].isna(), "agent/name"] = None

    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
