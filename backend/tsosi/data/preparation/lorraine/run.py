import os
import sys
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

NAME = "lorraine"
RAW_FOLDER = Path(BASE_DIR) / "_no_git/data/raw" / NAME
PREPARATION_FOLDER = Path(BASE_DIR) / "tsosi/data/preparation" / NAME
# Date of the e-mail with the data
DATE_DATA = "2026-10-23"

# SPARC Europe is out of scope, the other ones are not in TSOSI yet.
EXCLUDED_RECIPIENTS = [
    "SPARC Europe",
    "EOSC",
    "Fair Open Access Alliance",
    "Retraction watch",
    "Wikimedia France",
]


def main() -> None:
    raw_path = str(RAW_FOLDER / "tsosi_ul-couperin-inclus_2026-2016.xlsx")
    df = pd.read_excel(raw_path, dtype="str")
    df = df.map(clean_cell_value)

    # The contract dates were entered in the contract/id and
    # contract/description columns, contract/date_start and contract/date_end
    # are empty.
    mapping = {
        "institution/name": "recipient/name",
        "intermediary/name": "intermediary/name",
        "Amount en € TTC": "amount_ttc",
        "à défaut amount en € HT": "amount_ht",
        "à défaut amount en $": "amount_usd",
        "date_invoice": "date_invoice",
        "date_emitted": "date_emitted",
        "date_received": "date_received",
        "contract/id": "contract/date_start",
        "contract/description": "contract/date_end",
    }
    df = df[mapping.keys()].rename(columns=mapping)

    # Remove the time part of the dates read from Excel
    date_cols = [
        "date_invoice",
        "date_emitted",
        "date_received",
        "contract/date_start",
        "contract/date_end",
    ]
    df[date_cols] = df[date_cols].map(
        lambda x: x[:10] if isinstance(x, str) else x
    )

    # Amount: TTC first, then HT, then USD
    amounts = {
        col: pd.to_numeric(df[col], errors="coerce")
        for col in ["amount_ttc", "amount_ht", "amount_usd"]
    }
    df["amount"] = (
        amounts["amount_ttc"]
        .fillna(amounts["amount_ht"])
        .fillna(amounts["amount_usd"])
    )
    df["currency"] = None
    df.loc[amounts["amount_usd"].notna(), "currency"] = "USD"
    df.loc[
        amounts["amount_ttc"].notna() | amounts["amount_ht"].notna(),
        "currency",
    ] = "EUR"
    df = df[df["amount"].notna()]
    df = df[~df["recipient/name"].isin(EXCLUDED_RECIPIENTS)]

    # Manual fixes
    # The 2026 arXiv contract was entered with the 2025 dates
    mask = (df["recipient/name"] == "arXiv") & (
        df["date_invoice"] == "2026-10-21"
    )
    df.loc[mask, "contract/date_start"] = "2026-01-01"
    df.loc[mask, "contract/date_end"] = "2026-12-31"
    # The 2026 OpenCitations contract was entered with the 2025 invoice date
    mask = (df["recipient/name"] == "OpenCitations") & (
        df["contract/date_start"] == "2026-01-01"
    )
    df.loc[mask, "date_invoice"] = "2026-10-21"
    # The 1500 € HT paid to Make Data Count in 2025 are the 1766 € TTC
    # reported by MDC
    mask = (df["recipient/name"] == "Make data count") & (
        df["contract/date_start"] == "2025-01-01"
    )
    df.loc[mask, "amount"] = 1766
    # The $4000 paid to PKP in 2024 are the 4000 € of 2025 reported by PKP
    mask = (df["recipient/name"] == "Public Knowledge Project") & (
        df["contract/date_start"] == "2024-01-01"
    )
    df.loc[mask, "amount"] = 4000
    df.loc[mask, "currency"] = "EUR"
    df.loc[mask, "contract/date_start"] = "2025-01-01"
    df.loc[mask, "contract/date_end"] = "2025-12-31"
    df.loc[mask, "date_invoice"] = None
    # The 2024 OLH contract runs from April to April, as reported by OLH
    mask = (df["recipient/name"] == "Open Library of Humanities") & (
        df["contract/date_start"] == "2024-01-01"
    )
    df.loc[mask, "contract/date_start"] = "2024-04-03"
    df.loc[mask, "contract/date_end"] = "2025-04-02"
    # The 2019 DOAJ support went through Couperin
    mask = (df["recipient/name"] == "Directory of Open Access Journals") & (
        df["contract/date_start"] == "2019-01-01"
    )
    df.loc[mask, "intermediary/name"] = "Couperin"

    df = df.drop(columns=["amount_ttc", "amount_ht", "amount_usd"])

    # Add infra identifiers
    infrastructure_lookup = pd.read_csv(
        PREPARATION_FOLDER / "infrastructure_lookup.csv",
        delimiter=";",
        dtype=str,
    )
    df = df.merge(infrastructure_lookup, how="left")
    mask = (
        df["recipient/ror_id"].isna()
        & df["recipient/wikidata_id"].isna()
        & df["recipient/custom_id"].isna()
    )
    if mask.any():
        raise ValueError(
            f"Missing recipient identifiers: {df.loc[mask, 'recipient/name'].unique()}"
        )

    # Add intermediary identifiers
    consortium_lookup = pd.read_csv(
        PREPARATION_FOLDER / "consortium_lookup.csv",
        delimiter=";",
        dtype=str,
    )
    df = df.merge(consortium_lookup, how="left")
    mask = df["intermediary/name"].notna() & (
        df["intermediary/ror_id"].isna() & df["intermediary/wikidata_id"].isna()
    )
    if mask.any():
        raise ValueError(
            f"Missing intermediary identifiers: {df.loc[mask, 'intermediary/name'].unique()}"
        )

    export_path = str(RAW_FOLDER / f"{DATE_DATA}_{NAME}_full.xlsx")
    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
