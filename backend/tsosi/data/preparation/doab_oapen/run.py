import os
import sys
from datetime import date
from pathlib import Path

import django
import numpy as np
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

NAME = "doab"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def handle_sponsors(filename, sheet=0):
    raw_path = str(RAW_FOLDER / f"0_raw/{filename}")
    df = pd.read_excel(raw_path, sheet_name=sheet)
    mapping = {
        "Company": "emitter/name",
        "Country": "emitter/country",
        "Invoice preferences": "invoice_type",
        "Commitment period (years)": "commitment_period",
        "Sponsorship start date": "support_start_date",
        "Sponsorship end date": "support_end_date",
        "Amount (EUR)": "amount_eur",
        "Amount (USD)": "amount_usd",
        "Amount (GBP)": "amount_gbp",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df["support_start_date"] = pd.to_datetime(
        df["support_start_date"], errors="coerce", dayfirst=True
    ).dt.date
    df["support_end_date"] = pd.to_datetime(
        df["support_end_date"], errors="coerce", dayfirst=True
    ).dt.date
    df["source"] = Path(filename).stem
    return df


def handle_default(filename, sheet=0, date_format="%d/%m/%Y"):
    raw_path = str(RAW_FOLDER / f"0_raw/{filename}")
    df = pd.read_excel(raw_path, sheet_name=sheet)
    mapping = {
        "Company": "emitter/name",
        "Agent": "intermediary/name",
        "Country": "emitter/country",
        "Invoice preference": "invoice_type",
        "Commitment period (years)": "commitment_period",
        "Year": "year",
        "Support start date": "support_start_date",
        "Support end date": "support_end_date",
        "Annual amount (EUR)": "amount_eur",
        "Annual amount (USD)": "amount_usd",
        "Annual amount (GBP)": "amount_gbp",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df["support_start_date"] = pd.to_datetime(
        df["support_start_date"], errors="coerce", format=date_format
    ).dt.date
    df["support_end_date"] = pd.to_datetime(
        df["support_end_date"], errors="coerce", format=date_format
    ).dt.date
    df["source"] = Path(filename).stem
    return df


def handle_projection(filename, sheet=0):
    raw_path = str(RAW_FOLDER / f"0_raw/{filename}")
    df = pd.read_excel(raw_path, sheet_name=sheet)
    mapping = {
        "Institution": "emitter/name",
        "Agent/Contact": "intermediary/name",
        "Country": "emitter/country",
        "Invoice preferences": "invoice_type",
        "Commitment period (years)": "commitment_period",
        "Support Start Date": "support_start_date",
        "Support End Date": "support_end_date",
        "Annual Amount (EUR)": "amount_eur",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df["support_start_date"] = pd.to_datetime(
        df["support_start_date"], errors="coerce", dayfirst=True
    ).dt.date
    df["support_end_date"] = pd.to_datetime(
        df["support_end_date"], errors="coerce", dayfirst=True
    ).dt.date
    df["source"] = Path(filename).stem
    return df


def main() -> None:
    df = pd.concat(
        [
            handle_sponsors("2025-02-11-DOAB_Sponsorship_Report.xlsx"),
            handle_default(
                "TSOSI_OAPEN_Library_Supporters_Report_2026-05-12.xlsx",
                date_format="%m/%d/%Y",
            ),
            handle_default("2025-02-11-DOAB_Library_Report.xlsx"),
            handle_projection(
                "LibrarySupportProjections_OAPEN_DOAB_20231127_SD.xlsx", sheet=1
            ),
        ],
        ignore_index=True,
    )
    df = df.map(clean_cell_value)
    df.loc[:, ["amount", "currency"]] = None
    for currency in ["eur", "usd", "gbp"]:
        mask = df[f"amount_{currency}"].notna()
        df.loc[mask, "amount"] = df.loc[mask, f"amount_{currency}"]
        df.loc[mask, "currency"] = currency.upper()
    df = df[df["amount"].notna()].drop(
        columns=[f"amount_{currency}" for currency in ["eur", "usd", "gbp"]]
    )

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

    df[df["emitter/ror_id"].isna() & df["emitter/wikidata_id"].isna()][
        "emitter/name"
    ].unique().tolist()

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

    df[
        df["intermediary/ror_id"].isna()
        & df["intermediary/wikidata_id"].isna()
        & df["intermediary/name"].notna()
    ]["intermediary/name"].unique().tolist()

    df["duration"] = df.apply(
        lambda row: (
            round(
                ((row["support_end_date"] - row["support_start_date"]).days)
                / 365
            )
            if pd.notna(row["support_start_date"])
            and pd.notna(row["support_end_date"])
            else None
        ),
        axis=1,
    )
    ## Fix bad support_end_date
    mask = (
        (df["invoice_type"] != "Upfront")
        & (df["duration"] > 1)
        & (df["duration"] != df["commitment_period"])
    )
    df.loc[mask, "support_end_date"] = df.loc[mask].apply(
        lambda row: (
            row["support_start_date"]
            + pd.DateOffset(years=row["commitment_period"], days=-1)
            if pd.notna(row["support_start_date"])
            and pd.notna(row["commitment_period"])
            else row["support_end_date"]
        ),
        axis=1,
    )
    ## Explore rows that span multiple year
    mask = (df["invoice_type"] != "Upfront") & (df["duration"] > 1)
    rows = []
    for _, row in df.loc[mask].iterrows():
        for i in range(int(row.commitment_period)):
            new_row = row.copy()
            new_row.support_start_date = (
                row.support_start_date + pd.DateOffset(years=i)
            ).date()
            new_row.support_end_date = (
                row.support_start_date + pd.DateOffset(years=i + 1, days=-1)
            ).date()
            rows.append(new_row)
    df = pd.concat([df[~mask], pd.DataFrame(rows)], ignore_index=True)

    df = df.drop_duplicates(
        subset=[
            "emitter/ror_id",
            "emitter/wikidata_id",
            "intermediary/ror_id",
            "intermediary/wikidata_id",
            "support_start_date",
            "support_end_date",
            "amount",
            "currency",
        ]
    )

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_to_fix.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
