import pandas as pd
from django.db.models import F
from tsosi.models import Entity
from tsosi.models.static_data import (
    REGISTRY_CUSTOM,
    REGISTRY_ROR,
    REGISTRY_WIKIDATA,
)
from tsosi.models.transfert import (
    MATCH_CRITERIA_SAME_NAME_COUNTRY,
    MATCH_CRITERIA_SAME_NAME_ONLY,
    MATCH_CRITERIA_SAME_NAME_URL,
    MATCH_CRITERIA_SAME_PID,
)

from .utils import clean_null_values


def resolve_merging_chain(
    df: pd.DataFrame,
    id_col: str,
    merged_with_col: str,
    result_col: str,
    max_iterations: int = 10,
):
    """"""
    df_last_entity = df[[id_col, merged_with_col]]

    merged_next_col = "__merged_next"
    df_for_merge = df[[id_col, merged_with_col]].rename(
        columns={
            id_col: merged_with_col,
            merged_with_col: merged_next_col,
        }
    )

    count = 1
    # Keep updating the last entity until all merged_next are None
    while count <= max_iterations:
        count += 1
        # Obtain the next item in the chain
        df_last_entity = df_last_entity.merge(
            df_for_merge,
            on=merged_with_col,
            how="left",
        )

        # If no more updates (i.e., merged_with_col is None), break out of the loop
        if (df_last_entity[merged_next_col].isna()).all():
            break

        # Update the merged_with_col to propagate the last item of the chain
        update = df_last_entity.dropna(subset=merged_next_col)
        df_last_entity.loc[update.index, merged_with_col] = update[
            merged_next_col
        ]
        df_last_entity = df_last_entity.drop(columns=[merged_next_col])

    if count == max_iterations:
        raise Exception("Max nb of iterations for resolving the merged chain.")

    df[result_col] = df_last_entity[merged_with_col]


def matchable_entities() -> pd.DataFrame:
    """
    Return all the matchable entities from database.
    The returned DataFrame contains 1 entry per entity per identifier.
    """
    instances = Entity.objects.all().values(
        "id",
        "name",
        "country",
        "website",
        "merged_with_id",
        "is_matchable",
        "is_agent",
        identifier_value=F("identifiers__value"),
        identifier_registry=F("identifiers__registry_id"),
    )
    data = pd.DataFrame.from_records(instances)
    if data.empty:
        return data

    resolve_merging_chain(data, "id", "merged_with_id", "merged_with_id")
    data = data[data["is_matchable"] == True].drop(columns=["is_matchable"])

    # Rename identifier columns to ror_id & wikidata_id
    mapping = {
        REGISTRY_ROR: "ror_id",
        REGISTRY_WIKIDATA: "wikidata_id",
        REGISTRY_CUSTOM: "custom_id",
    }
    pids: list[pd.DataFrame] = []
    for r, col in mapping.items():
        subset = data[data["identifier_registry"] == r].copy()
        subset[col] = subset["identifier_value"]
        pids.append(subset.copy())

    ror_ids = data[data["identifier_registry"] == REGISTRY_ROR].copy()
    ror_ids["ror_id"] = ror_ids["identifier_value"]

    wikidata_ids = data[data["identifier_registry"] == REGISTRY_WIKIDATA].copy()
    wikidata_ids["wikidata_id"] = wikidata_ids["identifier_value"]

    custom_ids = data[data["identifier_registry"] == REGISTRY_CUSTOM].copy()
    custom_ids["custom_id"] = custom_ids["identifier_value"]

    pid_indexes = []
    for subset in pids:
        pid_indexes += subset.index.to_list()

    rest = data[~data.index.isin(pid_indexes)]

    result = pd.concat([*pids, rest], axis=0, ignore_index=True).drop(
        columns=["identifier_value", "identifier_registry"]
    )
    clean_null_values(result)
    return result


def create_merge_comments(original_value: str, final_value: str) -> str | None:
    return f"The originally matched entity {original_value} was merged with {final_value}."


def match_entities(
    to_match: pd.DataFrame,
    base_entities: pd.DataFrame,
    merged_with_id: bool = False,
):
    """
    Match the given entity dataframe with the base data.
    The matching is made using the columns: `name`, `country`, `website`,
    `ror_id`, `wikidata_id` of both input dataframes.
    The final matched entity ID is either the entity `id` column or the
    `merged_with_id` when the matched entity was merged with another one.
    """
    # Assert expected columns are present
    columns = [
        "name",
        "country",
        "website",
        "ror_id",
        "wikidata_id",
        "custom_id",
    ]
    df = to_match[columns].copy()
    columns.append("id")
    if merged_with_id:
        columns.append("merged_with_id")
    base = base_entities[columns].copy()

    df["name"] = df["name"].apply(
        lambda x: x if not isinstance(x, str) else x.strip().lower()
    )
    base["name"] = base["name"].apply(
        lambda x: x if not isinstance(x, str) else x.strip().lower()
    )
    original_id = "__original_id"
    df[original_id] = df.index

    # Result of matching is stored in entity_id & match_criteria column
    df["matched_id"] = None
    df["match_criteria"] = None

    # Match on PIDs
    # Input data with PIDs can only be matched on PIDs

    # Match on Custom IDs
    mask_custom = ~df["custom_id"].isnull()
    df_loc = df[mask_custom].copy()
    merged = df_loc.merge(
        base[["id", "custom_id"]], how="inner", on="custom_id"
    )
    if not merged.empty:
        merged["match_criteria"] = MATCH_CRITERIA_SAME_PID
        merged.set_index(original_id, inplace=True)
        df.loc[merged.index, "matched_id"] = merged["id"]
        df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Match on ROR
    mask_ror = ~df["ror_id"].isnull()
    df_loc = df[mask_ror].copy()
    merged = df_loc.merge(base[["id", "ror_id"]], how="inner", on="ror_id")
    if not merged.empty:
        merged["match_criteria"] = MATCH_CRITERIA_SAME_PID
        merged.set_index(original_id, inplace=True)
        df.loc[merged.index, "matched_id"] = merged["id"]
        df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Match on Wikidata
    mask_wikidata = ~df["wikidata_id"].isnull() & df["matched_id"].isnull()
    df_loc = df[mask_wikidata].copy()
    merged = df_loc.merge(
        base[["id", "wikidata_id"]], how="inner", on="wikidata_id"
    )
    if not merged.empty:
        merged["match_criteria"] = MATCH_CRITERIA_SAME_PID
        merged.set_index(original_id, inplace=True)
        df.loc[merged.index, "matched_id"] = merged["id"]
        df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Match on name & country
    mask_no_pid = (
        df["ror_id"].isnull()
        & df["wikidata_id"].isnull()
        & df["custom_id"].isnull()
    )
    mask_name_country = ~df["name"].isnull() & ~df["country"].isnull()
    df_loc = df[mask_no_pid & mask_name_country].copy()
    merged = df_loc.merge(
        base[["id", "name", "country"]],
        how="inner",
        on=["name", "country"],
    )
    if not merged.empty:
        merged["match_criteria"] = MATCH_CRITERIA_SAME_NAME_COUNTRY
        merged.set_index(original_id, inplace=True)
        df.loc[merged.index, "matched_id"] = merged["id"]
        df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Match on name & website
    mask_name_website = (
        ~df["name"].isnull()
        & ~df["website"].isnull()
        & df["matched_id"].isnull()
    )
    df_loc = df[mask_no_pid & mask_name_website].copy()
    merged = df_loc.merge(
        base[["id", "name", "website"]],
        how="inner",
        on=["name", "website"],
    )
    if not merged.empty:
        merged["match_criteria"] = MATCH_CRITERIA_SAME_NAME_URL
        merged.set_index(original_id, inplace=True)
        df.loc[merged.index, "matched_id"] = merged["id"]
        df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Match on name with entities having only name
    mask_name_only = (
        ~df["name"].isnull()
        & df["country"].isnull()
        & df["website"].isnull()
        & df["matched_id"].isnull()
    )
    df_loc = df[mask_no_pid & mask_name_only].copy()

    base_loc = base[
        base["country"].isnull()
        & base["website"].isnull()
        & base["ror_id"].isnull()
        & base["wikidata_id"].isnull()
    ]
    if not df_loc.empty and not base_loc.empty:
        merged = df_loc.merge(
            base_loc[["id", "name"]], how="inner", on=["name"]
        )
        if not merged.empty:
            merged["match_criteria"] = MATCH_CRITERIA_SAME_NAME_ONLY
            merged.set_index(original_id, inplace=True)
            df.loc[merged.index, "matched_id"] = merged["id"]
            df.loc[merged.index, "match_criteria"] = merged["match_criteria"]

    # Add results to original dataframe
    to_match.loc[df.index, "matched_id"] = df["matched_id"]
    to_match.loc[df.index, "match_criteria"] = df["match_criteria"]
    if merged_with_id:
        to_match.loc[:, "merged_with_id"] = to_match["matched_id"].map(
            base_entities.drop_duplicates(subset="id").set_index("id")[
                "merged_with_id"
            ]
        )
        to_match.loc[:, "entity_id"] = (
            to_match[["merged_with_id", "matched_id"]].bfill(axis=1).iloc[:, 0]
        )
        to_match.loc[:, "comments"] = None
        to_match.loc[:, "_diff"] = ~to_match["entity_id"].eq(
            to_match["matched_id"]
        )
        subset = to_match[to_match["_diff"] & ~to_match["entity_id"].isnull()]
        if not subset.empty:
            to_match.loc[subset.index, "comments"] = subset.apply(
                lambda x: create_merge_comments(
                    x["matched_id"], x["entity_id"]
                ),
                axis=1,
            )
        to_match.drop(
            columns=["_diff", "matched_id", "merged_with_id"], inplace=True
        )

    clean_null_values(to_match)
