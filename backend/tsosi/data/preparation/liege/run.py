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


def split_intermediaries(value: str | None) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    parts = [clean_cell_value(v) for v in str(value).split("+")]
    return [v for v in parts if v]


def main() -> None:
    raw_folder = Path(BASE_DIR) / "_no_git/data/raw/liege"
    raw_path = str(
        raw_folder / f"2025--TSOSI-data-schema-institution-liege.xlsx"
    )
    export_path = str(raw_folder / f"2026-02-26_liege_full.xlsx")
    df = pd.read_excel(raw_path)

    mapping = {
        "infrastructure/name": "recipient/name",
        "intermediary/name": "intermediary/name",
        "amount": "amount",
        "date_received": "date_received",
    }
    df = df.rename(columns=mapping)[mapping.values()]

    # Clean string values
    df.loc[:, ["recipient/name", "intermediary/name", "date_received"]] = df[
        ["recipient/name", "intermediary/name", "date_received"]
    ].map(clean_cell_value)

    # Add institution identifiers
    infrastructure_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/liege"
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

    intermediaries = df["intermediary/name"].apply(split_intermediaries)
    for i in range(1, MAX_AGENTS_PER_TRANSFER + 1):
        name_col = f"intermediary/name/{i}"
        values = intermediaries.apply(
            lambda values: values[i - 1] if len(values) >= i else None
        )
        if values.isna().all():
            break
        df[name_col] = values

    consortium_lookup_path = (
        Path(BASE_DIR)
        / "tsosi/data/preparation/liege"
        / "consortium_lookup.csv"
    )
    consortium_lookup = pd.read_csv(
        consortium_lookup_path, delimiter=";", dtype=str
    )
    consortium_lookup["intermediary/name"] = consortium_lookup[
        "intermediary/name"
    ].map(clean_cell_value)

    for i in range(1, MAX_AGENTS_PER_TRANSFER + 1):
        name_col = f"intermediary/name/{i}"
        if name_col not in df.columns:
            break
        renamed_lookup = consortium_lookup.rename(
            columns={
                "intermediary/name": name_col,
                "intermediary/ror_id": f"intermediary/ror_id/{i}",
                "intermediary/wikidata_id": f"intermediary/wikidata_id/{i}",
            }
        )
        df = df.merge(renamed_lookup, how="left", on=name_col)

    df.pop("intermediary/name")

    df.to_excel(export_path, index=False)


if __name__ == "__main__":
    main()
