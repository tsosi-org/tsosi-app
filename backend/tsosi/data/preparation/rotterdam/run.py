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

NAME = "rotterdam"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(
        RAW_FOLDER
        / "ce383572238d158a96014f5c7e10541b339d1839de85ceac28120dcd7e1.EURdata.07-07-26.xlsx"
    )
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "infrastructure/name": "recipient/name",
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
    df = df[df["amount"].notna() & (df["recipient/name"].notna())]

    # The dates entered as Excel dates were typed as DD-MM and read as MM-DD:
    # the invoices of the 2025 grants are of early December 2025, paid from
    # 8 to 15 December. Swap back the day and month when the day is <= 12.
    def fix_swapped_date(value):
        if not isinstance(value, str) or not value.endswith(" 00:00:00"):
            return value
        year, month, day = value[:10].split("-")
        if int(day) <= 12:
            month, day = day, month
        return f"{year}-{month}-{day}"

    for col in ["date_invoice", "date_sent"]:
        df[col] = df[col].map(fix_swapped_date)

    df = df.map(clean_cell_value)

    # Add infra identifiers
    infrastructure_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation"
        / NAME
        / "infrastructure_lookup.csv"
    )
    infrastructure_lookup = pd.read_csv(
        infrastructure_path, delimiter=";", dtype=str
    )
    df = df.merge(
        infrastructure_lookup,
        how="left",
    )
    df[
        df["recipient/ror_id"].isna()
        & df["recipient/wikidata_id"].isna()
        & df["recipient/custom_id"].isna()
    ]

    df = df[
        ~(
            df["recipient/ror_id"].isna()
            & df["recipient/wikidata_id"].isna()
            & df["recipient/custom_id"].isna()
        )
    ]

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
    df[
        df["intermediary/ror_id"].isna()
        & df["intermediary/wikidata_id"].isna()
        & df["intermediary/name"].notna()
    ]

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
