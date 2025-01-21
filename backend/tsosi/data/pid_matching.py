import asyncio
import logging
from datetime import date

import pandas as pd
from django.utils import timezone
from tsosi.data.pid_registry.ror import match_ror_records
from tsosi.models import Entity
from tsosi.models.identifier import MATCH_CRITERIA_EXACT_MATCH
from tsosi.models.static_data import REGISTRY_ROR
from tsosi.models.transfert import (
    TRANSFERT_ENTITY_TYPE_AGENT,
    TRANSFERT_ENTITY_TYPE_EMITTER,
)
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC

from .data_preparation import clean_cell_value, country_name_from_iso
from .enrichment import ingest_entity_identifier_relations

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


def match_entities_to_pid(
    entities: pd.DataFrame,
    limit: int | None = None,
    export_to_verify: bool = False,
):
    """
    Match ROR records to the given data and ingest the results.

    1 - Query the ROR API for organization matching.
    2 - Generate a spreadsheet with entities without trusted match
        for manual review and upload it somewhere.
    3 - Select matches to be automatically trusted and pass them to
        `enrich_entity_data`.
        This can be queued as a task.
    """
    if limit:
        entities = entities.head(limit)

    #### 1 - Query the ROR API
    ror_results = asyncio.run(match_ror_records(entities["name"]))
    df_matched = pd.concat([entities, ror_results], axis="columns")

    ror_match_mask = (df_matched["ror_match_score"] == 1) & (
        df_matched["ror_match_type"] == "EXACT"
    )

    #### 2 - Export entities with no trusted match for manual review
    if export_to_verify:
        to_verify = df_matched[~ror_match_mask][
            [
                "id",
                "name",
                "country",
                "website",
                "ror_matched_id",
                "ror_matched_name",
                "ror_match_score",
                "ror_error",
                "ror_error_message",
            ]
        ]
        to_verify["country"] = to_verify["country"].apply(country_name_from_iso)
        file_name = f"{date.today()}_ror_matching_to_verify.xlsx"
        to_verify.sort_values("name").to_excel(file_name, index=False)

    #### 3 - Handle trusted matches: ingest new relationships
    exact = (
        df_matched[ror_match_mask][["id", "ror_matched_id"]]
        .copy()
        .rename(
            columns={"id": "entity_id", "ror_matched_id": "identifier_value"}
        )
    )
    exact["match_source"] = MATCH_SOURCE_AUTOMATIC
    exact["match_criteria"] = MATCH_CRITERIA_EXACT_MATCH
    now = timezone.now()

    ingest_entity_identifier_relations(exact, REGISTRY_ROR, now)


def prepare_manual_matching(
    data: pd.DataFrame, name_column: str, limit: int | None = None
) -> pd.DataFrame:
    """
    Enrich the given data with the results of the ROR affiliation API.
    The following columns holding the affiliation matching result are added
    after the given `name_column`:
        - `ror_matched_id`
        - `ror_matched_name`
        - `ror_exact_match`.
    The following empty com
    """
    df = data.head(limit).copy() if limit else data.copy()
    logger.info(f"Preparing manual matching for {len(df)} entities.")

    initial_columns = list(df.columns)

    df["__name_clean"] = df[name_column].apply(clean_cell_value)
    df_match = df[~df["__name_clean"].isna()]

    # Get ror affiliation matching
    ror_results = asyncio.run(match_ror_records(df_match["__name_clean"]))
    result = pd.concat(
        [df_match.reset_index(drop=True), ror_results.reset_index(drop=True)],
        axis="columns",
    )
    result.index = df_match.index

    # Flag perfect match & rename
    result["ror_exact_match"] = (result["ror_match_score"] == 1) | (
        result["ror_match_type"] == "EXACT"
    )
    ror_columns = ["ror_matched_id", "ror_matched_name", "ror_exact_match"]
    result.rename(columns={c: f"_{c}" for c in ror_columns}, inplace=True)
    ror_columns = [f"_{c}" for c in ror_columns]

    # TODO: check that indexes are okay when merging, code seems strange
    df = df.merge(
        result[ror_columns],
        how="left",
        left_index=True,
        right_index=True,
    )
    # Add other columns used for manual completion
    other_manual_columns = [
        "_processed",
        "_remark",
        "_found_url",
        "_wikidata_id",
        "_name_from_wikidata",
        "_manual_ror_id",
        "_name_from_ror",
    ]
    for c in other_manual_columns:
        df[c] = None

    df["_ror_exact_match"] = df["_ror_exact_match"].apply(
        lambda x: True if pd.isnull(x) else x
    )

    columns_ordered = []
    for col in initial_columns:
        if col not in ror_columns:
            columns_ordered.append(col)
        if col == name_column:
            columns_ordered += other_manual_columns
            columns_ordered += ror_columns

    logger.info(
        f"Successfully prepared manual matching for {len(df)} entities."
    )
    return df[columns_ordered]


def process_enriched_data(
    data: pd.DataFrame, name_column: str, entity_type: str
) -> pd.DataFrame:
    """
    Outputs a clean, prepared Dataframe from enriched data
    (outputed from `prepare_manual_matching`).
    """
    logger.info("Processing enriched data.")

    df = data.copy(deep=True)
    allowed_entity_types = [
        TRANSFERT_ENTITY_TYPE_EMITTER,
        TRANSFERT_ENTITY_TYPE_AGENT,
    ]
    if entity_type not in allowed_entity_types:
        raise ValueError(
            f"Unvalid entity_type {entity_type}. "
            f"Only {allowed_entity_types} types are allowed."
        )

    # Discard useless columns
    discard_columns = [
        "_name_from_wikidata",
        "_name_from_ror",
        "_ror_matched_id",
        "_ror_matched_name",
        "_ror_exact_match",
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
    }

    def is_processed[T](val: T) -> bool:
        if isinstance(val, str):
            return val.strip().lower() == "true"
        elif isinstance(val, bool):
            return val
        return False

    mask = df["_processed"].apply(is_processed)

    final_enriched_columns = []
    for col_current, col_generic in enriched_columns.items():
        col_final = f"{entity_type}_{col_generic}"
        df.loc[mask.index, col_final] = df[col_current]
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
    return df[final_columns].copy()
