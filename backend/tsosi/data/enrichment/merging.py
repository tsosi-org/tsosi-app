import logging
from datetime import datetime

import pandas as pd
from django.db import transaction
from tsosi.data.db_utils import bulk_create_from_df, bulk_update_from_df
from tsosi.data.exceptions import DataException
from tsosi.models import Entity, Transfer, TransferEntityMatching
from tsosi.models.transfer import MATCH_CRITERIA_MERGED, TRANSFER_ENTITY_TYPES

logger = logging.getLogger(__name__)


@transaction.atomic
def merge_entities(entities: pd.DataFrame, date_update: datetime):
    """
    Merge the given entities.

    1 - Update the `merged_with` value of the entities to me merged.

    2 - Concatenate the static fields from the entity it was merged with.
        Note that Identifiers are not handled by this method so their
        re-assignement should be handled before calling this method.

    3 - Update all transfers referencing the original entity to reference
        the new one.

    4 - Add an entry in TransferEntityMatching for all the (Transfer, Entity)
        combinations.

    :param entities:    The DataFrame of entities to be merged.
                        It must contain the columns:

                        - `entity_id` - The ID of the entity to be merged
                        - `merged_with_id` - The ID of the entity to be merged
                            with
                        - `merged_criteria` - The merging criteria
                        - `match_criteria` - The match criteria to input in step 4
                        - `match_source` - The match source to input in step 4

    :param date_update: The datetime object to use as the update date.
    """
    # Prepare data
    # Check required columns and remove duplicate rows
    to_merge = entities.copy()
    to_merge["entity_id"] = to_merge["entity_id"].astype("string")
    to_merge["merged_with_id"] = to_merge["merged_with_id"].astype("string")
    to_merge = (
        to_merge[~to_merge["merged_with_id"].isnull()]
        .drop_duplicates(subset=["entity_id", "merged_with_id"])[
            [
                "entity_id",
                "merged_with_id",
                "merged_criteria",
                "match_criteria",
                "match_source",
            ]
        ]
        .copy()
    )
    merging_self = to_merge[to_merge["entity_id"] == to_merge["merged_with_id"]]
    if not merging_self.empty:
        logger.warning(
            "Requested self-merging for the following entities, "
            "discarded from the merged entities: \n"
            f"{merging_self["entity_id"].drop_duplicates().to_list()}"
        )
        to_merge = to_merge.drop(merging_self.index).reset_index(drop=True)

    if to_merge.empty:
        return

    # TODO: entities inputed in the function have null match_criteria.
    # This should be set beforehand and not in this function.
    to_merge["match_criteria"] = to_merge["match_criteria"].fillna(
        MATCH_CRITERIA_MERGED
    )

    # 0 - Check for duplicated entity_id inputs
    grouped_by_entity = (
        to_merge.groupby("entity_id")
        .agg(
            ids=pd.NamedAgg(column="merged_with_id", aggfunc=lambda x: list(x)),
            number=pd.NamedAgg(
                column="merged_with_id", aggfunc=lambda x: x.count()
            ),
        )
        .reset_index()
    )
    duplicates = grouped_by_entity[grouped_by_entity["number"] > 1]
    if len(duplicates) > 0:
        raise DataException(
            f"""
            Error while merging entities.
            The following entities appear several times with different entities
            to be merged with:
            {duplicates.set_index("entity_id")["ids"].to_dict()}
            """
        )

    logger.info(f"Merging {len(to_merge)} entities.")

    update_fields = [
        "raw_name",
        "raw_country",
        "raw_website",
        "description",
        "short_name",
    ]

    # 1 - Update the entities to be merged
    mapping = to_merge.set_index("entity_id")
    entity_list = mapping.index.to_list()
    e_to_update = pd.DataFrame.from_records(
        Entity.objects.filter(id__in=entity_list).values("id", *update_fields)
    )
    if len(e_to_update) == 0:
        logger.info("No entity to merge.")
        return

    e_to_update["id"] = e_to_update["id"].astype("string")
    e_to_update["merged_with_id"] = e_to_update["id"].map(
        mapping["merged_with_id"]
    )
    e_to_update["merged_criteria"] = e_to_update["id"].map(
        mapping["merged_criteria"]
    )
    e_to_update["date_last_updated"] = date_update
    e_to_update["is_active"] = False
    bulk_update_from_df(
        Entity,
        e_to_update,
        fields=[
            "id",
            "merged_with_id",
            "merged_criteria",
            "date_last_updated",
            "is_active",
        ],
    )
    logger.info(f"Updated {len(to_merge)} Entity records.")

    # 2 - Update entities that were merged with other
    m_entities = pd.DataFrame.from_records(
        Entity.objects.filter(
            id__in=e_to_update["merged_with_id"].to_list()
        ).values("id", *update_fields)
    )
    m_entities["id"] = m_entities["id"].astype("string")
    old_data = (
        e_to_update.groupby("merged_with_id")[update_fields]
        .first()
        .add_prefix("_merged_")
        .reset_index()
    )
    old_data.rename(columns={"merged_with_id": "id"}, inplace=True)
    m_entities = m_entities.merge(old_data, how="left", on="id")
    # Check for diff and update
    for f in update_fields:
        f_merged = f"_merged_{f}"
        f_clc = f"_clc_{f}"
        m_entities[f_clc] = m_entities[[f, f_merged]].bfill(axis=1).iloc[:, 0]
        f_diff = f"_diff_{f}"
        m_entities[f_diff] = ~m_entities[f].eq(m_entities[f_clc])

    m_entities["_diff"] = m_entities[[f"_diff_{f}" for f in update_fields]].any(
        axis=1
    )
    cols = ["id", *[f"_clc_{f}" for f in update_fields]]
    m_entities = m_entities[m_entities["_diff"]][cols].copy()
    m_entities.rename(
        columns={f"_clc_{f}": f for f in update_fields}, inplace=True
    )
    m_entities["date_last_updated"] = date_update
    bulk_update_from_df(Entity, m_entities, m_entities.columns.to_list())

    for e_type in TRANSFER_ENTITY_TYPES:
        # 3 - Update all transfers referencing these entities
        entity_field = f"{e_type}_id"
        kwargs = {f"{entity_field}__in": entity_list}
        t_to_update = pd.DataFrame.from_records(
            Transfer.objects.filter(**kwargs).values("id", entity_field)
        )
        if t_to_update.empty:
            continue

        t_to_update[entity_field] = t_to_update[entity_field].astype("string")
        t_to_update["original_entity_id"] = t_to_update[entity_field].copy()
        t_to_update[entity_field] = t_to_update[entity_field].map(
            mapping["merged_with_id"]
        )
        t_to_update["date_last_updated"] = date_update

        fields = ["id", entity_field, "date_last_updated"]
        bulk_update_from_df(Transfer, t_to_update, fields)
        logger.info(
            f"Updated {len(t_to_update)} Transfer records with entity type `{e_type}`"
        )

        # 3 - Create new TransferEntityMatching records
        t_to_update["transfer_entity_type"] = e_type
        t_to_update = t_to_update.merge(
            to_merge[["entity_id", "match_criteria", "match_source"]].rename(
                columns={"entity_id": "original_entity_id"}
            ),
            on="original_entity_id",
            how="left",
        )
        t_to_update["date_created"] = date_update
        t_to_update.rename(
            columns={"id": "transfer_id", entity_field: "entity_id"},
            inplace=True,
        )

        fields = [
            "transfer_id",
            "transfer_entity_type",
            "entity_id",
            "match_criteria",
            "match_source",
            "date_created",
            "date_last_updated",
        ]
        bulk_create_from_df(TransferEntityMatching, t_to_update, fields)
        logger.info(
            f"Created {len(t_to_update)} TransferEntityMatching records for e_type: `{e_type}`."
        )
    logger.info(f"Successfully merged {len(to_merge)} entities.")
