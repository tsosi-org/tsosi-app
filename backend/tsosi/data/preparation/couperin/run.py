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
    raw_folder = Path(BASE_DIR) / "_no_git/data/raw/couperin"
    raw_path = str(raw_folder / f"Couperin_Soutiens_SO_20260203_fixed.xlsx")
    export_path = str(raw_folder / f"2026-02-03_couperin_full.xlsx")

    infra_lookup_path = (
        Path(BASE_DIR) / "tsosi/data/preparation/couperin" / "infra_lookup.csv"
    )
    institution_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/couperin"
        / "institution_lookup.csv"
    )

    df = pd.read_excel(raw_path, sheet_name="Feuil1").iloc[:, :10]
    infra_lookup = pd.read_csv(infra_lookup_path, delimiter=";", dtype=str)
    institution_lookup = pd.read_csv(
        institution_lookup_path, delimiter=";", dtype=str
    )

    df.columns = [
        "recipient/name",
        "couperin",
        "convention",
        "emitter/name",
        "emitter/type",
        "emitter/ror_id_error",
        "emitter/ror_id",
        "date_start",
        "amount",
        "3-year",
    ]
    df = df[
        [
            "recipient/name",
            "couperin",
            "emitter/name",
            "emitter/ror_id",
            "date_start",
            "amount",
            "3-year",
        ]
    ]

    # Add agent data based on row color...
    is_couperin = df["couperin"] == "oui"
    df["agent/name"] = None
    df["agent/ror_id"] = None
    df.loc[is_couperin, "agent/name"] = "Couperin"
    df.loc[is_couperin, "agent/ror_id"] = "035c9qf67"  # ROR ID of Couperin
    df = df.drop(columns=["couperin"])

    # Filter to keep only rows with couperin as agent
    df = df[is_couperin]

    # Filter to keep only couperin campaign infra
    df = df[df["recipient/name"].isin(infra_lookup["name"])]

    # Filter to remove zero amounts
    df = df[df["amount"] != 0]

    # Clean ROR IDs (remove https://ror.org/ prefix)
    mask = df["emitter/ror_id"].notna()
    df.loc[mask, "emitter/ror_id"] = df.loc[mask, "emitter/ror_id"].str.replace(
        "https://ror.org/", ""
    )

    # Add infra identifiers
    for field in ["ror_id", "wikidata_id", "custom_id"]:
        df[f"recipient/{field}"] = df["recipient/name"].replace(
            infra_lookup[["name", field]].set_index("name")[field]
        )

    # Add institution identifiers
    for field in ["ror_id", "wikidata_id"]:
        mask = df["emitter/name"].isin(institution_lookup["name"])
        df.loc[mask, f"emitter/{field}"] = df.loc[mask, "emitter/name"].replace(
            institution_lookup[["name", field]].set_index("name")[field]
        )

    # Add local emitter info
    df["emitter/local"] = None
    local_names = {
        "COMUE  de TOULOUSE": "COMUE",
    }
    for name, local_name in local_names.items():
        mask = df["emitter/name"] == name
        df.loc[mask, "emitter/local"] = local_name

    # Add dates
    df["date_end"] = df["date_start"]
    mask = df["3-year"] == "oui"
    df.loc[mask, "date_end"] = df.loc[mask, "date_start"] + 3

    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
