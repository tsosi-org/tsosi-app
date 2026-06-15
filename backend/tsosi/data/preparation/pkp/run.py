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

NAME = "pkp"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / "PKP_2026--TSOSI-data-infra.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "institution/name": "emitter/name",
        "intermediary/name": "agent/name",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "contract/date_start": "date_start",
        "contract/date_end": "date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df.map(clean_cell_value)
    df = df[df["currency"].notnull()]

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

    df = df[
        ~(
            df["date_invoice"].isnull()
            & df["date_start"].isnull()
            & df["date_end"].isnull()
        )
    ]

    df = df[~(df["agent/name"] == "Couperin")]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
