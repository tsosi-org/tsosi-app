import asyncio
import logging

import pandas as pd
from tsosi.data.pid_registry.ror import match_ror_records
from tsosi.models import Entity
from tsosi.models.static_data import REGISTRY_ROR
from tsosi.models.transfert import (
    TRANSFERT_ENTITY_TYPE_AGENT,
    TRANSFERT_ENTITY_TYPE_EMITTER,
)
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC, MATCH_SOURCE_MANUAL

from .preparation.cleaning_utils import (
    clean_cell_value,
    country_iso_from_name,
    country_name_from_iso,
)
from .utils import clean_null_values

logger = logging.getLogger("console_only")


def entities_with_no_ror() -> pd.DataFrame:
    """
    Returns the Dataframe of entities with no ROR identifier.
    Columns are `id`, `name`, `county`, `website`
    """
    entities = Entity.objects.exclude(
        identifiers__registry_id=REGISTRY_ROR
    ).order_by("name")

    df = pd.DataFrame.from_records(
        entities.values("id", "name", "country", "website")
    )
    # Cast UUID field to str
    df["id"] = df["id"].apply(str)
    return df


def prepare_manual_matching(
    data: pd.DataFrame,
    name_column: str,
    country_column: str | None = None,
    prefix: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Enrich the given data with the results of the ROR affiliation API.
    The following columns holding the affiliation matching result are added
    after the given `name_column`:
        - `ror_matched_id`
        - `ror_matched_name`
        - `ror_exact_match`.

    The following empty columns are also added to prepare for manual matching:
        - `_processed`
        - `_remark`
        - `_found_url`
        - `_wikidata_id`
        - `_name_from_wikidata`
        - `_manual_ror_id`
        - `_name_from_ror`
    """
    df = data.head(limit).copy() if limit else data.copy()
    logger.info(f"Preparing manual matching for {len(df)} entities.")

    initial_columns = list(df.columns)

    df["__name_clean"] = df[name_column].apply(clean_cell_value)
    df_match = df[~df["__name_clean"].isna()]
    # Get the country ISO alpha-2 code when the country is present
    if country_column:
        clean_null_values(df_match)
        df_match["__country_clean"] = df_match[country_column].apply(
            lambda x: country_iso_from_name(x, error=True)
        )
    else:
        df_match["__country_clean"] = None

    clean_null_values(df_match)
    # Get ror affiliation matching
    ror_results = asyncio.run(
        match_ror_records(df_match["__name_clean"], df_match["__country_clean"])
    )
    result = pd.concat(
        [df_match.reset_index(drop=True), ror_results.reset_index(drop=True)],
        axis="columns",
    )
    result.index = df_match.index

    result["ror_matched_country"] = result["ror_matched_country"].apply(
        country_name_from_iso
    )
    ror_columns = [
        "ror_matched_id",
        "ror_perfect_match",
        "ror_matched_name",
        "ror_matched_country",
    ]
    result.rename(columns={c: f"_{c}" for c in ror_columns}, inplace=True)
    ror_columns = [f"_{c}" for c in ror_columns]

    df = df.merge(
        result[ror_columns],
        how="left",
        left_index=True,
        right_index=True,
    )
    # Add other columns used for manual completion
    df["_processed"] = df["_ror_perfect_match"].map({True: True, False: None})
    other_manual_columns = [
        "_remark",
        "_found_url",
        "_wikidata_id",
        "_name_from_wikidata",
        "_manual_ror_id",
        "_name_from_ror",
    ]
    for c in other_manual_columns:
        df[c] = None

    columns_ordered = []
    for col in initial_columns:
        if col not in ror_columns:
            columns_ordered.append(col)
        if col == name_column:
            columns_ordered.append("_processed")
            columns_ordered += other_manual_columns
            columns_ordered += ror_columns

    result = df[columns_ordered]
    if prefix is not None:
        result.rename(
            columns={
                col: f"{prefix}_{col}"
                for col in other_manual_columns + ror_columns
            }
        )
    logger.info(
        f"Successfully prepared manual matching for {len(df)} entities."
    )
    return result


def is_true(val) -> bool:
    if isinstance(val, str):
        return val.strip().lower() == "true"
    elif isinstance(val, bool):
        return val
    elif isinstance(val, (int, float)):
        return val == 1
    return False


def process_enriched_data(
    data: pd.DataFrame, name_column: str, entity_type: str
) -> pd.DataFrame:
    """
    Outputs a clean, prepared Dataframe from enriched data
    (outputed from `prepare_manual_matching`).
    """
    logger.info("Processing enriched data.")

    allowed_entity_types = [
        TRANSFERT_ENTITY_TYPE_EMITTER,
        TRANSFERT_ENTITY_TYPE_AGENT,
    ]
    if entity_type not in allowed_entity_types:
        raise ValueError(
            f"Unvalid entity_type {entity_type}. "
            f"Only {allowed_entity_types} types are allowed."
        )
    if name_column not in data.columns:
        raise ValueError(f"Name column {name_column} is not in the input data.")
    df = data.copy(deep=True)
    df["_match_source"] = MATCH_SOURCE_MANUAL
    # Fill manual ROR ID from the matched ID when it's a perfect match.
    perfect_match_col = "_ror_perfect_match"
    if perfect_match_col in df.columns:
        mask = df[perfect_match_col].apply(is_true)
        df_filtered = df[mask]
        df.loc[df_filtered.index, "_manual_ror_id"] = df_filtered[
            "_ror_matched_id"
        ]
        df.loc[df_filtered.index, "_match_source"] = MATCH_SOURCE_AUTOMATIC

    # Discard useless columns
    discard_columns = [
        "_name_from_wikidata",
        "_name_from_ror",
        "_ror_matched_id",
        "_ror_matched_name",
        "_ror_exact_match",
        "_ror_perfect_match",
    ]
    for c in discard_columns:
        if c not in df.columns:
            continue
        del df[c]
    # Useful columns
    enriched_columns = {
        "_remark": "matching_remark",
        "_found_url": "website",
        "_wikidata_id": "wikidata_id",
        "_manual_ror_id": "ror_id",
        "_match_source": "match_source",
    }

    mask = df["_processed"].apply(is_true)
    df_filtered = df[mask]
    final_enriched_columns = []
    for col_current, col_generic in enriched_columns.items():
        col_final = f"{entity_type}_{col_generic}"
        df.loc[df_filtered.index, col_final] = df_filtered[col_current]
        del df[col_current]
        final_enriched_columns.append(col_final)

    del df["_processed"]

    # Re-order the dataframe columns to add the enrichment columns
    # right after the entity name
    final_columns = []
    for c in df.columns:
        if c in final_enriched_columns:
            continue
        final_columns.append(c)
        if c == name_column:
            final_columns = final_columns + final_enriched_columns

    logger.info("Processed enriched data.")
    clean_null_values(df)
    return df[final_columns].copy()
