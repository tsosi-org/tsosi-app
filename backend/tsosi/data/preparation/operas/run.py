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

NAME = "operas"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def handle_2023() -> pd.DataFrame:
    raw_path = str(RAW_FOLDER / f"OPERAS2023.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "Emitter": "emitter/name",
        "Date": "date_received",
        "Currency": "currency",
        "Value": "amount",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df["support_type"] = None
    df.loc[df["amount"].isna(), "support_type"] = df.loc[
        df["amount"].isna(), "emitter/name"
    ]
    df.loc[:, "support_type"] = df["support_type"].ffill()
    df.loc[:, "support_type"] = df["support_type"].replace(
        {
            "Projects": "grant and project funding",
            "Membership": "membership",
            "Subventions": "support",
        }
    )
    df = df[df["amount"].notna() & (df["emitter/name"].notna())]
    return df


def handle_2024_2025() -> pd.DataFrame:
    raw_path = str(RAW_FOLDER / f"Pierre-OPERAS2024-25.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping_2024 = {
        "Emitter": "emitter/name",
        "Value": "amount",
    }
    mapping_2025 = {
        "Emitter": "emitter/name",
        "Value.1": "amount",
    }
    df_2024 = df.rename(columns=mapping_2024)[mapping_2024.values()]
    df_2024["date_received"] = "2024"
    df_2025 = df.rename(columns=mapping_2025)[mapping_2025.values()]
    df_2025["date_received"] = "2025"
    df = pd.concat([df_2024, df_2025], ignore_index=True)
    df["support_type"] = None
    df.loc[df["amount"].isna(), "support_type"] = df.loc[
        df["amount"].isna(), "emitter/name"
    ]
    df.loc[:, "support_type"] = df["support_type"].ffill()
    df.loc[:, "support_type"] = df["support_type"].replace(
        {
            "Projects": "grant and project funding",
            "Membership": "membership",
            "Subventions": "support",
        }
    )
    df = df[
        df["amount"].notna()
        & (df["amount"] != "0")
        & (df["emitter/name"].notna())
    ]
    df["currency"] = "EUR"
    return df


def main() -> None:
    df = pd.concat(
        [
            handle_2023(),
            handle_2024_2025(),
        ],
        ignore_index=True,
    )
    df = df.map(clean_cell_value)

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
    # df[
    #     df["emitter/ror_id"].isna()
    #     & df["emitter/wikidata_id"].isna()
    #     & df["emitter/custom_id"].isna()
    # ]["emitter/name"].unique().tolist()

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
