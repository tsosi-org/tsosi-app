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

from tsosi.data.ingestion.core import MAX_AGENTS_PER_TRANSFER
from tsosi.data.preparation.cleaning_utils import clean_cell_value


def main() -> None:
    raw_folder = Path(BASE_DIR) / "_no_git/data/raw/leuven"
    raw_path = str(raw_folder / f"20260309_TSOSI_template_completed.xlsx")
    export_path = str(raw_folder / f"2026-03-09_leuven_full.xlsx")
    df = pd.read_excel(raw_path)

    mapping = {
        "infrastructure/name": "recipient/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_emitted": "date_emitted",
        "date_received": "date_received",
        "contract/date_start": "contract/date_start",
        "contract/date_end": "contract/date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    df.loc[:, ["recipient/name", "intermediary/name"]] = df[
        ["recipient/name", "intermediary/name"]
    ].map(clean_cell_value)

    # Add infra identifiers
    infrastructure_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/leuven"
        / "infrastructure_lookup.csv"
    )
    infrastructure_lookup = pd.read_csv(
        infrastructure_path, delimiter=";", dtype=str
    )
    df = df.merge(
        infrastructure_lookup,
        how="left",
    )

    # df[df["recipient/ror_id"].isna() & df["recipient/wikidata_id"].isna()]
    consortium_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/leuven"
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(
        consortium_lookup_path, delimiter=";", dtype=str
    )
    consortium_lookup["intermediary/name"] = consortium_lookup[
        "intermediary/name"
    ].map(clean_cell_value)
    df = df.merge(
        consortium_lookup,
        how="left",
    )

    df["hide_amount"] = ~df["amount"].map(
        lambda x: isinstance(x, int) | isinstance(x, float)
    )
    df.loc[df["hide_amount"], "amount"] = None

    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
