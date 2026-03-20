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

raw_folder = Path(BASE_DIR) / "_no_git/data/raw/pci"
raw_path = str(raw_folder / "2025-03-03_PCI_Funding_Report.xlsx")
raw_25_path = str(raw_folder / "2025-02-23_PCI.xlsx")
id_path = str(raw_folder / "2025-01-06_PCI_Funding_Data_Identifiers.xlsx")
export_path = str(raw_folder / f"2026-02-24_pci_full.xlsx")

df = pd.read_excel(raw_path, dtype=str)
df = df.map(clean_cell_value)
mapping = {
    "From organization": "emitter/name",
    # "Category": "emitter/type",
    # "Website": "emitter/website",
    "Year": "year",
    "Amount": "amount",
    "Via?": "agent/name",
}
df = df.rename(columns=mapping)[mapping.values()]

df25 = pd.read_excel(raw_25_path, 1, header=None)
df25 = df25.map(clean_cell_value)
columns = ["emitter/name", "amount"]
df25.columns = columns

mask = df25["emitter/name"].str.find(r" - via Couperin") != -1
df25["emitter/name"] = df25["emitter/name"].str.replace(r" - via Couperin", "")
df25["emitter/name"] = df25["emitter/name"].map(clean_cell_value)
df25["agent/name"] = None
df25.loc[mask, "agent/name"] = "Couperin"
df25["year"] = 2025

df = pd.concat([df, df25], ignore_index=True)

ids_emitters = pd.read_excel(id_path, "Emitters")
ids_emitters = ids_emitters.map(clean_cell_value)
mapping = {
    "Institution/origine du soutien": "emitter/name",
    "ROR": "emitter/ror_id",
    "wikidata": "emitter/wikidata_id",
    # "Country": "emitter/country",
    # "Website": "emitter/website",
    # "Type of structure": "emitter/type",
}
ids_emitters = ids_emitters.rename(columns=mapping)[mapping.values()]
ids_emitters = ids_emitters.drop_duplicates()

institution_lookup_path = (
    Path(BASE_DIR) / "tsosi/data/preparation/pci" / "institution_lookup.csv"
)
institution_lookup = pd.read_csv(
    institution_lookup_path, delimiter=";", dtype=str
)
ids_emitters = pd.concat(
    [ids_emitters, institution_lookup], ignore_index=True
).drop_duplicates(["emitter/name"], keep="last")

df = df.merge(ids_emitters, on="emitter/name", how="left")

# df[df["emitter/ror_id"].isnull() & df["emitter/wikidata_id"].isnull()]

ids_consortiums = pd.read_excel(id_path, "Consortiums")
ids_consortiums = ids_consortiums.map(clean_cell_value)
## Map consortiums to the transfers df
mapping = {
    "Consortia": "agent/name",
    "ROR": "agent/ror_id",
    "wikidata": "agent/wikidata_id",
    # "Website": "agent/website",
}
ids_consortiums = ids_consortiums.rename(columns=mapping)[mapping.values()]
ids_consortiums = ids_consortiums.drop_duplicates()

agent_lookup_path = (
    Path(BASE_DIR) / "tsosi/data/preparation/pci" / "agent_lookup.csv"
)
agent_lookup = pd.read_csv(agent_lookup_path, delimiter=";", dtype=str)
ids_consortiums = pd.concat(
    [ids_consortiums, agent_lookup], ignore_index=True
).drop_duplicates(["agent/name"], keep="last")

df = df.merge(ids_consortiums, on="agent/name", how="left")

df.to_excel(export_path, index=False)
