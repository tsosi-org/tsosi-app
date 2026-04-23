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

NAME = "pci"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / "2025-03-03_PCI_Funding_Report.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "From organization": "emitter/name",
        # "Category": "emitter/type",
        # "Website": "emitter/website",
        "Year": "year",
        "Amount": "amount",
        "Via?": "agent/name",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df.map(clean_cell_value)

    raw_25_path = str(RAW_FOLDER / "2025-02-23_PCI.xlsx")
    df25 = pd.read_excel(raw_25_path, 1, header=None)
    columns = ["emitter/name", "amount"]
    df25.columns = columns
    df25 = df25.map(clean_cell_value)

    mask = df25["emitter/name"].str.find(r" - via Couperin") != -1
    df25["emitter/name"] = df25["emitter/name"].str.replace(
        r" - via Couperin", ""
    )
    df25["emitter/name"] = df25["emitter/name"].map(clean_cell_value)
    df25["agent/name"] = None
    df25.loc[mask, "agent/name"] = "Couperin"
    df25["year"] = 2025

    df = pd.concat([df, df25], ignore_index=True)

    institution_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "institution_lookup.csv"
    )
    institution_lookup = pd.read_csv(
        institution_lookup_path, delimiter=";", dtype=str
    )

    df = df.merge(institution_lookup, how="left")

    df[df["emitter/ror_id"].isnull() & df["emitter/wikidata_id"].isnull()]

    agent_lookup_path = (
        Path(BASE_DIR) / "tsosi/data/preparation" / NAME / "agent_lookup.csv"
    )
    agent_lookup = pd.read_csv(agent_lookup_path, delimiter=";", dtype=str)

    df = df.merge(agent_lookup, how="left")

    df[
        ~df["agent/name"].isnull()
        & df["agent/ror_id"].isnull()
        & df["agent/wikidata_id"].isnull()
    ]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
