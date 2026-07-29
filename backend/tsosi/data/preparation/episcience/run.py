import os
import sys
from datetime import date
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

NAME = "olh"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / "TSOSI-data-schema-infra-template-olh.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "institution/name": "emitter/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_sent": "date_sent",
        "date_received": "date_received",
        "contract/date_start": "date_start",
        "contract/date_end": "date_end",
        "support_type": "support_type",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df[df["amount"].notna() & (df["emitter/name"].notna())]
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
    mask = (
        df["emitter/ror_id"].isna()
        & df["emitter/wikidata_id"].isna()
        & df["emitter/custom_id"].isna()
    )

    consortium_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(consortium_path, delimiter=";", dtype=str)
    df = df.merge(
        consortium_lookup,
        how="left",
    )
    mask = (
        df["intermediary/name"].notna()
        & df["intermediary/ror_id"].isna()
        & df["intermediary/wikidata_id"].isna()
        & df["intermediary/name"].notna()
    )

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
