import logging
from datetime import datetime

import pandas as pd
from django.db import transaction
from tsosi.models import Entity, Transfert, TransfertEntityMatching
from tsosi.models.transfert import TRANSFERT_ENTITY_TYPES

from .db_utils import bulk_create_from_df, bulk_update_from_df

logger = logging.getLogger(__name__)


@transaction.atomic
def merge_entities(entities: pd.DataFrame, date_update: datetime):
    """
    TODO: Concatenate all relevant data when merging entities:
        - raw name/country/URL
        - transfert PIDs

    Merge entities. The input dataframe must contain the column `id` of the
    entity to be merged and the column `merge_id` of the entity
    to be merged with.
    1 - Update the `merged_with` value of the entities to me merged.
    2 - Update all transferts referencing the original entity to reference
        the new one.
    3 - Add an entry in TransfertEntityMatching for all the (Transfert, Entity)
        combinations.
    """
    to_merge = (
        entities[~entities["merged_with_id"].isnull()]
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
    if len(entities) == 0:
        return

    entities["entity_id"] = entities["entity_id"].apply(str)
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
        raise Exception(
            f"""
            Error while merging entities.
            The following entities appear several times with different entities
            to be merged with:
            {duplicates.set_index("entity_id")["ids"].to_dict()}
            """
        )

    logger.info(f"Merging {len(to_merge)} entities.")

    # 1 - Update the entities to be merged
    mapping = to_merge.set_index("entity_id")
    entity_list = mapping.index.to_list()
    e_to_update = pd.DataFrame.from_records(
        Entity.objects.filter(id__in=entity_list).values(
            "id", "date_last_updated"
        )
    )
    if len(e_to_update) == 0:
        logger.info("No entity to merge.")
        return

    e_to_update["id"] = e_to_update["id"].apply(str)
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

    for e_type in TRANSFERT_ENTITY_TYPES:
        # 2 - Update all transferts referencing these entities
        entity_field = f"{e_type}_id"
        kwargs = {f"{entity_field}__in": entity_list}
        t_to_update = pd.DataFrame.from_records(
            Transfert.objects.filter(**kwargs).values("id", entity_field)
        )
        if t_to_update.empty:
            continue
        t_to_update["id"] = t_to_update["id"].apply(str)
        t_to_update[entity_field] = t_to_update[entity_field].apply(str)
        t_to_update["original_entity_id"] = t_to_update[entity_field].copy()
        t_to_update[entity_field] = t_to_update[entity_field].map(
            mapping["merged_with_id"]
        )
        t_to_update["date_last_updated"] = date_update

        fields = ["id", entity_field, "date_last_updated"]
        bulk_update_from_df(Transfert, t_to_update, fields)
        logger.info(
            f"Updated {len(t_to_update)} Transfert records with entity type `{e_type}`"
        )

        # 3 - Create new TransfertEntityMatching records
        t_to_update["transfert_entity_type"] = e_type
        t_to_update = t_to_update.merge(
            to_merge[["entity_id", "match_criteria", "match_source"]].rename(
                columns={"entity_id": "original_entity_id"}
            ),
            on="original_entity_id",
            how="left",
        )
        t_to_update["date_created"] = date_update
        t_to_update.rename(columns={"id", "transfert_id"}, inplace=True)
        fields = [
            "transfert_id",
            "transfert_entity_type",
            "entity_id",
            "match_criteria",
            "match_source",
            "date_created",
            "date_last_updated",
        ]
        bulk_create_from_df(TransfertEntityMatching, t_to_update, fields)
        logger.info(
            f"Created {len(t_to_update)} TransfertEntityMatching records for e_type: `{e_type}`."
        )
    logger.info(f"Successfully merged {len(to_merge)} entities.")
