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

NAME = "episciences"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME


def main() -> None:
    raw_path = str(RAW_FOLDER / "2025--TSOSI-data-schema-EPISCIENCES.xlsx")
    df = pd.read_excel(raw_path, dtype=str)
    mapping = {
        "institution/name": "emitter/name",
        "institution/ror_id": "emitter/ror_id",
        "institution/wikidata_id": "emitter/wikidata_id",
        "institution/country": "emitter/country",
        "intermediary/name": "intermediary/name",
        "intermediary/ror_id": "intermediary/ror_id",
        "intermediary/wikidata_id": "intermediary/wikidata_id",
        "intermediary/country": "intermediary/country",
        "amount": "amount",
        "currency": "currency",
        "date_invoice": "date_invoice",
        "date_emitted": "date_sent",
        "date_received": "date_received",
        "contract/date_start": "date_start",
        "contract/date_end": "date_end",
    }
    df = df.rename(columns=mapping)[mapping.values()]
    df = df[df["amount"].notna() & (df["emitter/name"].notna())]
    df = df.map(clean_cell_value)
    df["emitter/ror_id"] = df["emitter/ror_id"].replace(
        r"^https://ror.org/", "", regex=True
    )
    df["intermediary/ror_id"] = df["intermediary/ror_id"].replace(
        r"^https://ror.org/", "", regex=True
    )

    # Couperin supports are ingested from Couperin's own data
    df = df[df["intermediary/ror_id"] != "035c9qf67"]

    # Only keep supports actually received: at least one date, none in the
    # future
    date_cols = ["date_invoice", "date_sent", "date_received"]
    dates = df[date_cols].apply(pd.to_datetime)
    df = df[
        dates.notna().any(axis=1) & (dates.max(axis=1) <= pd.Timestamp.today())
    ]

    # ETH Zürich paid its 3 years at once, while CSAL declares 3 yearly
    # transfers: split it the same way so that they merge
    eth = df["emitter/ror_id"] == "05a28rw58"
    eth_rows = pd.concat([df[eth]] * 3, ignore_index=True)
    eth_rows["amount"] = (eth_rows["amount"].astype(float) / 3).astype(str)
    eth_rows["date_received"] = ["2025", "2026", "2027"]
    df = pd.concat([df[~eth], eth_rows], ignore_index=True)

    mask = df["emitter/ror_id"].isna() & df["emitter/wikidata_id"].isna()
    df[mask]["emitter/name"].unique()

    mask = (
        df["intermediary/name"].notna()
        & df["intermediary/ror_id"].isna()
        & df["intermediary/wikidata_id"].isna()
        & df["intermediary/name"].notna()
    )
    df[mask]["intermediary/name"].unique()

    export_path = str(
        RAW_FOLDER / f"{date.today().isoformat()}_{NAME}_full.xlsx"
    )
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
