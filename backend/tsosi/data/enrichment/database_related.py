"""
Tasks only involving TSOSI own database.
"""

import logging
from datetime import UTC, date, datetime

import pandas as pd
from django.db import transaction
from django.db.models import Count, F, Max, QuerySet
from django.utils import timezone
from tsosi.app_settings import app_settings
from tsosi.data.db_utils import (
    IDENTIFIER_CREATE_FIELDS,
    IDENTIFIER_MATCHING_CREATE_FIELDS,
    DateExtremas,
    bulk_create_from_df,
    bulk_update_from_df,
    date_extremas_from_queryset,
)
from tsosi.data.exceptions import DataException
from tsosi.data.pid_registry.ror import (
    ROR_EXTRACT_MAPPING,
    ror_record_extractor,
)
from tsosi.data.pid_registry.wikidata import WIKIDATA_EXTRACT_MAPPING
from tsosi.data.preparation.cleaning_utils import clean_cell_value, clean_url
from tsosi.data.signals import identifiers_created
from tsosi.data.task_result import TaskResult
from tsosi.data.utils import clean_null_values
from tsosi.models import (
    Entity,
    EntityName,
    Identifier,
    IdentifierEntityMatching,
    IdentifierVersion,
    InfrastructureDetails,
    Transfer,
)
from tsosi.models.date import DATE_PRECISION_YEAR, Date
from tsosi.models.identifier import (
    MATCH_CRITERIA_FROM_ROR,
    MATCH_CRITERIA_FROM_WIKIDATA,
)
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA
from tsosi.models.transfer import MATCH_CRITERIA_MERGED, TRANSFER_ENTITY_TYPES
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC

from .merging import merge_entities

logger = logging.getLogger(__name__)


@transaction.atomic
def ingest_entity_identifier_relations(
    data: pd.DataFrame, registry_id: str, date_update: datetime
):
    """
    Ingest the given entity <-> identifier relations for the given registry.

    0 - Drop duplicates tuples (PID, entity) in input.
        Check coherency for duplicated entities.

    1 - Get the existing (PID value, Entity) relations & drop duplicated
        tuples (PID, entity) between input & existing

    2 - Get duplicated entities between input & mapping. Detach the existing
        relations for those entities (a new one will be created).
        --then-> Update existing relations with detached identifiers.

    3 - Handle identifiers in input that exist but are not attached
        to any entity
        --then-> Update existing relations

    4 - Create all new PIDs not in the existing relations
        --then-> Update existing relations with new relations.

    5 - All remaining rows in input should be merged according to the existing
        relations, as all identifiers in input now exist and are attached
        to an entity.


    :param data:            The dataframe of entity - identifier relations.
                            It must contain the columns:

                            - `entity_id`
                            - `identifier_value`
                            - `match_source`
                            - `match_criteria`
    :param registry_id:     The ID of the considered PID registry.
    :param date_update:     The date to register as `date_last_updated`
    """

    new_relations = data.copy(deep=True)
    new_relations["entity_id"] = new_relations["entity_id"].astype("string")

    ## Consistency check - duplicated entity_id in the input data.
    new_relations = new_relations.drop_duplicates(
        subset=["entity_id", "identifier_value"]
    )[["entity_id", "identifier_value", "match_source", "match_criteria"]]
    grouped_by_entity = (
        new_relations.groupby("entity_id")
        .agg(
            pids=pd.NamedAgg(
                column="identifier_value", aggfunc=lambda x: list(x)
            ),
            number=pd.NamedAgg(
                column="identifier_value", aggfunc=lambda x: x.count()
            ),
        )
        .reset_index()
    )
    duplicates = grouped_by_entity[grouped_by_entity["number"] > 1]
    if not duplicates.empty:
        raise DataException(
            f"""
            Error while ingesting entity - identifier relations.
            The following entities have different associated identifiers:
            {duplicates.set_index("entity_id")["pids"].to_dict()}
            """
        )

    logger.info(
        f"Ingesting {len(new_relations)} Identifier <-> Entity relations."
    )

    # 1 -   Retrieve the existing (PID -> Entity) relations. Drop the input
    #       relations that already exist.
    columns = ["id", "value", "entity_id"]
    ex_identifiers = Identifier.objects.filter(registry__id=registry_id).values(
        *columns
    )
    existing_relations = (
        pd.DataFrame.from_records(ex_identifiers, columns=columns)
        .rename(columns={"value": "identifier_value", "id": "identifier_id"})
        .set_index("identifier_id")
    )
    existing_relations["entity_id"] = existing_relations["entity_id"].astype(
        "string"
    )
    existing_relations["relation"] = list(
        zip(
            existing_relations["entity_id"],
            existing_relations["identifier_value"],
        )
    )

    new_relations["relation"] = list(
        zip(new_relations["entity_id"], new_relations["identifier_value"])
    )
    new_relations.set_index("entity_id")

    mask = ~new_relations["relation"].isin(existing_relations["relation"])
    new_relations = new_relations[mask].copy()

    # 2 -   Get duplicated entities between input & existing and
    #       detach associated identifiers
    mask = existing_relations["entity_id"].isin(new_relations["entity_id"])
    rel_to_detach = existing_relations[mask]
    if not rel_to_detach.empty:
        logger.info(f"Detaching {len(rel_to_detach)} existing relations.")
        Identifier.objects.filter(id__in=rel_to_detach.index.to_list()).update(
            entity=None, date_last_updated=date_update
        )
        IdentifierEntityMatching.objects.filter(
            identifier__id__in=rel_to_detach.index.to_list(),
            date_end__isnull=True,
        ).update(
            date_end=date_update,
            date_last_updated=date_update,
            comments=f"New identifier of registry {registry_id} for the entity.",
        )
        existing_relations.loc[rel_to_detach.index, "entity_id"] = None

    # 3 - Handle input relations involving existing detached identifiers
    detached_relations = existing_relations[
        existing_relations["entity_id"].isna()
    ]
    mask = new_relations["identifier_value"].isin(
        detached_relations["identifier_value"]
    )
    pid_to_update = new_relations[mask].drop_duplicates(
        subset="identifier_value"
    )

    if not pid_to_update.empty:
        pid_to_update = pid_to_update.merge(
            existing_relations["identifier_value"].reset_index(),
            on="identifier_value",
            how="left",
        )
        pid_to_update["date_last_updated"] = date_update
        cols = {
            "identifier_id": "id",
            "entity_id": "entity_id",
            "date_last_updated": "date_last_updated",
        }
        identifiers_for_update = pid_to_update.rename(columns=cols)
        bulk_update_from_df(Identifier, identifiers_for_update, cols.values())

        # Create IdentifierEntityMatching entries
        pid_to_update["date_created"] = date_update
        pid_to_update["date_start"] = date_update
        bulk_create_from_df(
            IdentifierEntityMatching,
            pid_to_update,
            IDENTIFIER_MATCHING_CREATE_FIELDS,
        )

        # Update existing relations with updated identifiers.
        mask = existing_relations.index.isin(pid_to_update["identifier_id"])
        existing_relations.loc[mask, "entity_id"] = existing_relations.loc[
            mask
        ].index.map(pid_to_update.set_index("identifier_id")["entity_id"])

    # 4 -   Create new PIDs not in existing relations.
    mask = ~new_relations["identifier_value"].isin(
        existing_relations["identifier_value"]
    )
    pid_to_create = new_relations[mask].drop_duplicates(
        subset="identifier_value"
    )
    if not pid_to_create.empty:
        pid_to_create["registry_id"] = registry_id
        pid_to_create["value"] = pid_to_create["identifier_value"].copy()
        pid_to_create["date_created"] = date_update
        pid_to_create["date_last_updated"] = date_update
        pid_to_create["date_start"] = date_update

        bulk_create_from_df(
            Identifier, pid_to_create, IDENTIFIER_CREATE_FIELDS, "identifier_id"
        )
        bulk_create_from_df(
            IdentifierEntityMatching,
            pid_to_create,
            IDENTIFIER_MATCHING_CREATE_FIELDS,
        )

        new_relations.loc[pid_to_create.index, "identifier_id"] = pid_to_create[
            "identifier_id"
        ]
        existing_relations: pd.DataFrame = pd.concat(
            [
                existing_relations,
                pid_to_create.set_index("identifier_id")[
                    ["entity_id", "identifier_value"]
                ],
            ],
            axis=0,
        )
        logger.info(f"Created {len(pid_to_create)} Identifier records.")

    # 5 - Merge remaining entities
    mask = ~new_relations["entity_id"].isin(existing_relations["entity_id"])
    to_merge = new_relations[mask].copy()

    to_merge["merged_with_id"] = to_merge["identifier_value"].map(
        existing_relations.reset_index().set_index("identifier_value")[
            "entity_id"
        ]
    )
    to_merge["merged_criteria"] = to_merge["identifier_value"].apply(
        lambda x: f"Entity merged because of the same {registry_id} PID value: {x}"
    )
    to_merge["match_criteria"] = MATCH_CRITERIA_MERGED
    merge_entities(to_merge, date_update)

    logger.info(f"Finished ingesting new Identifier - Entity relations.")


def active_identifiers() -> pd.DataFrame:
    """
    Return identifiers with a current version attached to an Entity.
    """
    instances = Identifier.objects.filter(
        entity__isnull=False, current_version__id__isnull=False
    ).values(
        "id",
        "registry_id",
        "value",
        version_id=F("current_version__id"),
        version_value=F("current_version__value"),
    )
    return pd.DataFrame.from_records(instances)


def entities_with_identifier_data() -> pd.DataFrame:
    """
    Return the entities and associated identifier data.
    This dataset is used to update the Entity's calculated fields based
    on PID records.
    """
    entities = (
        Entity.objects.filter(
            is_active=True, identifiers__current_version__isnull=False
        )
        .distinct("id")  # de-duplicated entities from the above left join
        .values(
            "id",
            # Raw values
            "raw_name",
            "raw_country",
            "raw_website",
            "raw_logo_url",
            # Values to be clc
            "name",
            "country",
            "website",
            "wikipedia_url",
            "logo_url",
            "coordinates",
            "date_inception",
            # Other values that may be updated
            "date_logo_fetched",
            "date_wikipedia_fetched",
        )
    )
    entities = pd.DataFrame.from_records(entities)
    if entities.empty:
        return pd.DataFrame()
    identifiers = Identifier.objects.filter(
        entity__isnull=False, current_version__isnull=False
    ).values(
        "registry_id",
        "entity_id",
        record=F("current_version__value"),
    )
    identifiers = pd.DataFrame.from_records(identifiers)
    if identifiers.empty:
        return pd.DataFrame()

    # Extract ROR record data
    ror_ids = identifiers[
        identifiers["registry_id"] == REGISTRY_ROR
    ].reset_index(drop=True)
    ror_extract = pd.json_normalize(
        ror_ids["record"].apply(ror_record_extractor), max_level=1
    )
    ror_ids = pd.concat([ror_ids, ror_extract], axis=1)
    ror_ids.drop(columns=["registry_id", "record"], inplace=True)
    entities = entities.merge(
        ror_ids,
        left_on="id",
        right_on="entity_id",
        how="left",
    )

    # Extract Wikidata record data
    wikidata_ids = identifiers[
        identifiers["registry_id"] == REGISTRY_WIKIDATA
    ].reset_index(drop=True)
    wikidata_extract = pd.json_normalize(wikidata_ids["record"])
    col_mapping = {c: f"wikidata_{c}" for c in wikidata_extract.columns}
    wikidata_extract.rename(
        columns=col_mapping,
        inplace=True,
    )
    wikidata_ids = pd.concat(
        [wikidata_ids, wikidata_extract],
        axis=1,
    )
    wikidata_ids.drop(columns=["registry_id", "record"], inplace=True)
    entities = entities.merge(
        wikidata_ids,
        left_on="id",
        right_on="entity_id",
        how="left",
    )

    # Format and clean record data.
    # entities["id"] = entities["id"].apply(str)
    # Add missing columns, if any
    expected_cols = [
        *[f"ror_{name}" for name in ROR_EXTRACT_MAPPING.keys()],
        *[f"wikidata_{name}" for name in WIKIDATA_EXTRACT_MAPPING.values()],
    ]
    for col in expected_cols:
        if col in entities.columns:
            entities[col] = entities[col].apply(clean_cell_value)
            continue
        entities[col] = None

    url_cols = [
        "raw_website",
        "raw_logo_url",
        "website",
        "ror_website",
        "ror_wikipedia_url",
        "wikidata_website",
        "wikidata_wikipedia_url",
    ]
    for col in url_cols:
        if not col in entities.columns:
            continue
        entities[col] = entities[col].apply(clean_url)

    date_cols = ["ror_date_inception", "wikidata_date_inception"]

    def make_date(x) -> datetime | None:
        if pd.isna(x):
            return None
        elif isinstance(x, datetime):
            return x
        elif isinstance(x, date):
            return datetime(x.year, x.month, x.day, tzinfo=UTC)
        elif isinstance(x, str):
            return datetime.fromisoformat(x)
        else:
            logger.warning(f"Non-supported date-like input: {x}")
            return None

    for col in date_cols:
        if not col in entities.columns:
            continue
        entities[col] = entities[col].apply(make_date)
    return entities


def update_entity_from_pid_records() -> TaskResult:
    """
    Retrieve useful data from PID records and update the referenced entity
    accordingly.
    Update all the simple clc fields: name, country, website, logo_url,
    wikipedia_url.
    Also update fields based on above updates: date_logo_fetched,
    date_wikipedia_fetched.
    """
    logger.info("Updating entity from PID records.")
    result = TaskResult(partial=False)

    entities = entities_with_identifier_data()
    if entities.empty:
        return result
    clean_null_values(entities)
    # This holds for each CLC field the data to use in which order,
    # moving to the next if null.
    clc_field_priority = {
        "name": ["ror_name", "wikidata_name", "raw_name"],
        "country": ["ror_country", "wikidata_country", "raw_country"],
        "website": ["ror_website", "wikidata_website", "raw_website"],
        "logo_url": ["wikidata_logo_url", "raw_logo_url"],
        "wikipedia_url": ["wikidata_wikipedia_url", "ror_wikipedia_url"],
        "coordinates": ["wikidata_coordinates", "ror_coordinates"],
        "date_inception": ["ror_date_inception", "wikidata_date_inception"],
        # The following fields are to be updated according to other fields
        "date_logo_fetched": ["date_logo_fetched"],
        "date_wikipedia_fetched": ["date_wikipedia_fetched"],
    }
    # Compute the value for each field and check if there's a diff with existing
    # data
    cols = ["id"]
    for field, f_list in clc_field_priority.items():
        f_clc = f"{field}_clc"
        entities[f_clc] = entities[f_list].bfill(axis=1).iloc[:, 0]
        f_diff = f"{field}_diff"
        entities[f_diff] = ~entities[field].eq(entities[f_clc])
        cols.append(f_clc)
        cols.append(f_diff)

    # Select entities with new data to be updated
    entities["diff"] = entities[
        [f"{f}_diff" for f in clc_field_priority.keys()]
    ].any(axis=1)
    entities_to_update = entities[entities["diff"]][cols].copy()
    entities_to_update.rename(
        columns={f"{f}_clc": f for f in clc_field_priority.keys()}, inplace=True
    )
    # Side effects
    # date_logo_fetched must be set to null when the logo_url changes
    # date_wikipedia_fetched must be set to null when the wikipedia_url changes
    mask = entities_to_update["logo_url_diff"]
    entities_to_update.loc[mask, "date_logo_fetched"] = None

    mask = entities_to_update["wikipedia_url_diff"]
    entities_to_update.loc[mask, "date_wikipedia_fetched"] = None

    entities_to_update["date_last_updated"] = timezone.now()
    cols = ["id", *clc_field_priority.keys(), "date_last_updated"]

    bulk_update_from_df(Entity, entities_to_update, cols)

    logger.info(
        f"Updated {len(entities_to_update)} Entity record from PID data."
    )
    result.data_modified = True
    return result


def new_identifiers_from_records(registry_id: str) -> TaskResult:
    """
    Retrieve and ingest new entity <-> identifier relationships from PID data.
    This has to be performed sequentially per registry so that the used
    dataset is refreshed after entity/identifier update.
    """
    result = TaskResult(partial=False)

    if registry_id == REGISTRY_ROR:
        base_col = "ror_id"
        new_col = "wikidata_ror_id"
        match_criteria = MATCH_CRITERIA_FROM_WIKIDATA
        force = False
    elif registry_id == REGISTRY_WIKIDATA:
        base_col = "wikidata_id"
        new_col = "ror_wikidata_id"
        match_criteria = MATCH_CRITERIA_FROM_ROR
        force = True
    else:
        raise DataException(f"Unsupported registry: {registry_id}")

    logger.info(
        f"Creating new {registry_id} identifiers from existing records."
    )
    entities = entities_with_identifier_data()
    if entities.empty:
        logger.info(f"No {registry_id} identifier to create.")
        return result

    entities = entities[
        [
            "id",
            "name",
            "ror_id",
            "ror_wikidata_id",
            "wikidata_id",
            "wikidata_ror_id",
        ]
    ].copy()

    entities["_doublon"] = ~(
        entities[base_col].isna() | entities[new_col].isna()
    )
    entities["_diff"] = ~(entities[base_col].eq(entities[new_col]))
    mismatch = entities[entities["_doublon"] & entities["_diff"]]
    if not mismatch.empty:
        msgs = []
        msgs.append(
            f"The following entities have mismatching {registry_id} PID:"
        )

        for _, row in mismatch.iterrows():
            msgs.append(
                f"Entity: {row["name"]} -- "
                f"PID in DB: {row[base_col]} -- "
                f"New PID from record: {row[new_col]}"
            )
        if force:
            msgs = ["[NOT DROPPING THE RELS]", *msgs]
        else:
            entities.drop(mismatch.index, inplace=True)
        logger.warning("\n".join(msgs))

    # We update all relations having a different new value, if not null
    # The dropping of problematic relations should be done before
    # entities["_new_pid"] = entities[base_col].isna() & ~entities[new_col].isna()
    entities["_new_pid"] = entities["_diff"] & ~entities[new_col].isna()
    entities.drop(columns=["_diff", "_doublon"])
    new_rels = entities[entities["_new_pid"]][["id", new_col]].reset_index(
        drop=True
    )
    if new_rels.empty:
        logger.info(f"No {registry_id} identifier to create.")
        return result

    new_rels.rename(
        columns={"id": "entity_id", new_col: "identifier_value"}, inplace=True
    )
    new_rels["match_source"] = MATCH_SOURCE_AUTOMATIC
    new_rels["match_criteria"] = match_criteria

    now = timezone.now()
    ingest_entity_identifier_relations(new_rels, registry_id, now)

    result.data_modified = True
    identifiers_created.send(None, registries=[registry_id])
    return result


def update_transfer_date_clc():
    """
    Update the `date_clc` field for transfers based on the various
    date fields.
    """
    logger.info("Updating transfer CLC date.")
    instances = Transfer.objects.filter(merged_into__isnull=True).values(
        "id",
        "date_invoice",
        "date_payment_recipient",
        "date_payment_emitter",
        "date_start",
    )
    if len(instances) == 0:
        logger.info("No transfer to update CLC date for.")
        return

    data = pd.DataFrame.from_records(instances)

    # The date should not be precised if it's derived from the
    # start date of the supporting period
    def update_date_start(d: dict | None):
        if d is None:
            return d
        new_date = Date(**d)
        new_date.precision = DATE_PRECISION_YEAR
        return new_date.serialize()

    data["date_start"] = data["date_start"].apply(update_date_start)
    data["date_clc"] = (
        data[
            [
                "date_payment_recipient",
                "date_payment_emitter",
                "date_invoice",
                "date_start",
            ]
        ]
        .bfill(axis=1)
        .iloc[:, 0]
    )
    data["date_last_updated"] = timezone.now()
    columns = ["id", "date_clc", "date_last_updated"]
    bulk_update_from_df(Transfer, data, columns)


def update_entity_active_status():
    """
    Update the active status entities.
    An entity is active if it's a partner or if it's referenced in 1+ transfer.
    """
    logger.info("Updating active entities.")
    instances = Entity.objects.annotate(
        emitter_nb=Count("transfer_as_emitter"),
        recipient_nb=Count("transfer_as_recipient"),
        agent_nb=Count("transfer_as_agent"),
    ).values(
        "id",
        "is_partner",
        "emitter_nb",
        "recipient_nb",
        "agent_nb",
        "merged_with",
    )
    data = pd.DataFrame.from_records(instances)
    data["is_active"] = data["merged_with"].isna() & (
        data["is_partner"]
        | (data["emitter_nb"] > 0)
        | (data["recipient_nb"] > 0)
        | (data["agent_nb"] > 0)
    )
    bulk_update_from_df(Entity, data, ["id", "is_active"])


def update_entity_roles_clc():
    """
    Update the `is_emitter`, `is_recipient`, `is_agent` booleans according
    to the transfer data.
    """
    logger.info("Updating entity roles.")

    transfer_cols = [f"{t}_id" for t in TRANSFER_ENTITY_TYPES]
    transfers = pd.DataFrame.from_records(
        Transfer.objects.filter(merged_into__isnull=True).values(
            "id", *transfer_cols
        )
    )
    entities_cols = [f"is_{t}" for t in TRANSFER_ENTITY_TYPES]
    entities = pd.DataFrame.from_records(
        Entity.objects.filter(is_active=True).values("id", *entities_cols)
    )
    if transfers.empty or entities.empty:
        logger.info("No transfer or no active entity, no role update to make.")
        return

    for t in TRANSFER_ENTITY_TYPES:
        e_of_type = transfers[f"{t}_id"].drop_duplicates()
        entities[f"new_is_{t}"] = entities["id"].isin(e_of_type)
        entities[f"{t}_diff"] = entities[f"is_{t}"] != entities[f"new_is_{t}"]

    diff_cols = [f"{t}_diff" for t in TRANSFER_ENTITY_TYPES]
    e_to_update = entities[entities[diff_cols].any(axis=1)].copy()

    if e_to_update.empty:
        logger.info("No role update to make for existing entities.")
        return

    e_to_update["date_last_updated"] = timezone.now()
    cols_for_update = {
        "id": "id",
        "date_last_updated": "date_last_updated",
        **{f"new_is_{t}": f"is_{t}" for t in TRANSFER_ENTITY_TYPES},
    }
    e_to_update = e_to_update[cols_for_update.keys()].rename(
        columns=cols_for_update
    )
    cols_for_update = list(cols_for_update.values())

    bulk_update_from_df(Entity, e_to_update, cols_for_update)

    logger.info(f"Updated {len(e_to_update)} Entity's role.")


def update_infrastructure_metrics():
    """
    Compute infrastructure metrics from the transfers. This updates or creates
    the  `InfrastructureDetails` instances attached to infrastructure Entities.
    """
    logger.info("Updating infrastructure metrics.")
    # Min & max transfer dates per recipient
    dates = date_extremas_from_queryset(
        Transfer.objects.filter(merged_into__isnull=True),
        ["date_clc"],
        groupby=["recipient_id"],
    )
    dates: dict[str, DateExtremas] = {
        d["recipient_id"]: d["_extremas"] for d in dates
    }

    total_transfers = Count("transfer_as_recipient")
    date_source_max = Max(
        "transfer_as_recipient__data_load_sources__date_data_obtained"
    )

    entities = (
        Entity.objects.filter(
            is_recipient=True, transfer_as_recipient__merged_into__isnull=True
        )
        .annotate(total_transfers=total_transfers)
        .annotate(date_last_update=date_source_max)
        .values(
            "id",
            "total_transfers",
            "date_last_update",
            "infrastructure_details",
        )
    )
    data = pd.DataFrame.from_records(entities)
    if data.empty:
        logger.info(f"No data to update infrastructure metrics for.")
        return

    data["dates"] = data["id"].map(dates)
    data["date_data_start"] = data["dates"].apply(
        lambda x: x.min if not pd.isna(x) else x
    )
    data["date_data_end"] = data["dates"].apply(
        lambda x: x.max if not pd.isna(x) else x
    )

    data["date_data_update"] = data["date_last_update"]

    no_details_mask = data["infrastructure_details"].isna()
    details_to_create = data[no_details_mask].copy()
    if not details_to_create.empty:
        details_to_create["entity_id"] = details_to_create["id"]
        bulk_create_from_df(
            InfrastructureDetails,
            details_to_create,
            [
                "entity_id",
                "date_data_start",
                "date_data_end",
                "date_data_update",
            ],
        )

    details_to_update = data[~no_details_mask].copy()
    if not details_to_update.empty:
        details_to_update["id"] = details_to_update["infrastructure_details"]
        bulk_update_from_df(
            InfrastructureDetails,
            details_to_update,
            [
                "id",
                "date_data_start",
                "date_data_end",
                "date_data_update",
            ],
        )
    logger.info(f"Updated {len(data)} infrastructure metrics.")


def identifier_versions_for_cleaning() -> pd.DataFrame:
    """ """
    queryset = IdentifierVersion.objects.select_related("identifier").values(
        "id",
        "identifier_id",
        "value",
        "date_start",
        "date_end",
        registry_id=F("identifier__registry_id"),
    )

    data = pd.DataFrame.from_records(queryset)
    if data.empty:
        return data

    # Remove unique version per ID
    grouped = data.groupby("identifier_id")["id"].count().reset_index()
    to_remove_list = grouped[grouped["id"] == 1]["identifier_id"].to_list()
    to_drop = data[data["identifier_id"].isin(to_remove_list)]
    data = data.drop(to_drop.index).reset_index(drop=True)

    return data


def clean_identifier_versions():
    """
    Analyze and clean multiple versions of the same identifier.
    Versions without significant change w/ the previous one should be discarded.
    """
    data = identifier_versions_for_cleaning()
    if data.empty:
        logger.info("No identifier versions to process.")
        return

    # Extract useful data from ROR records.
    # Wikidata records are already processed when queried.
    ror_mask = data["registry_id"] == REGISTRY_ROR
    data.loc[ror_mask.index, "value"] = data[ror_mask]["value"].apply(
        ror_record_extractor
    )

    # Sort versions by date to compute diff between successive versions
    data = data.sort_values(["identifier_id", "date_start"])
    data: pd.DataFrame = pd.concat(
        [
            data,
            data[["identifier_id", "value"]].add_prefix("_next_").shift(-1),
        ],
        axis=1,
    )

    data["_value_same"] = data["value"].eq(data["_next_value"])
    # Whether the next row should be merged with the current one
    data["_merge_next"] = (
        data["identifier_id"] == data["_next_identifier_id"]
    ) & data["_value_same"]
    # Used for cumsum.
    # The versions with same `_merge_cumsum` should be merged together
    # The value is updated only when the previous row's `_merge_next` is false
    data["_merge_incr"] = data["_merge_next"].map({True: 0, False: 1})
    data["_merge_cumsum"] = data["_merge_incr"].cumsum().shift(1, fill_value=0)

    # We can now merge the rows with equal identifier_id & _merge_cumsum
    grouped = (
        data.groupby(["identifier_id", "_merge_cumsum"])
        .agg(
            id=pd.NamedAgg(column="id", aggfunc="first"),
            date_start=pd.NamedAgg(column="date_start", aggfunc="min"),
            date_end_max=pd.NamedAgg(column="date_end", aggfunc="max"),
            date_end_null=pd.NamedAgg(
                column="date_end", aggfunc=lambda x: x.isna().any()
            ),
            merged_ids_list=pd.NamedAgg(column="id", aggfunc=lambda x: list(x)),
            group_count=pd.NamedAgg(column="id", aggfunc="count"),
        )
        .reset_index()
    )
    grouped["date_end"] = grouped["date_end_max"]
    mask = grouped["date_end_null"]
    grouped.loc[mask, "date_end"] = pd.NaT
    grouped["has_merged"] = grouped["group_count"] > 1

    # Delete all versions not in grouped
    v_kept_ids = grouped["id"].to_list()
    v_to_delete = data[~data["id"].isin(v_kept_ids)]["id"].to_list()
    if v_to_delete:
        IdentifierVersion.objects.filter(id__in=v_to_delete).delete()
        logger.info(f"Deleted {len(v_to_delete)} redondant IdentifierVersion.")

    # Update versions with updated data
    now = timezone.now()

    v_to_update = grouped[grouped["has_merged"]].copy()
    if v_to_update.empty:
        return

    clean_null_values(v_to_update)
    v_to_update["date_last_updated"] = now
    bulk_update_from_df(
        IdentifierVersion,
        v_to_update,
        ["id", "date_start", "date_end", "date_last_updated"],
    )
    logger.info(
        f"Updated {len(v_to_update)} IdentifierVersion with merged ones."
    )

    # Update identifier's new current version
    id_to_update = v_to_update[v_to_update["date_end"].isna()].copy()
    if id_to_update.empty:
        return

    id_to_update = id_to_update[
        ["id", "identifier_id", "date_last_updated"]
    ].rename(columns={"id": "current_version_id", "identifier_id": "id"})
    bulk_update_from_df(
        Identifier,
        id_to_update,
        ["id", "current_version_id", "date_last_updated"],
    )


def update_entity_names():
    """
    Regenerate the entity names table from the identifier records.
    """
    logger.info("Updating entity names.")

    entities = entities_with_identifier_data()
    if entities.empty:
        return

    cols = ["id", "name", "ror_names"]
    entities = entities[~entities["ror_names"].isna()][cols].copy()

    data = entities.explode("ror_names").reset_index(drop=True)
    data = pd.concat(
        [
            data.drop(columns=["ror_names"]),
            pd.json_normalize(data["ror_names"]),
        ],
        axis=1,
    )
    names = data[data["value"] != data["name"]].drop_duplicates(
        subset=["id", "value"]
    )

    # Delete all existing aliases from the given registry
    EntityName.objects.filter(registry_id=REGISTRY_ROR).delete()

    # Insert names
    names.rename(columns={"id": "entity_id"}, inplace=True)
    names["registry_id"] = REGISTRY_ROR
    names["date_created"] = timezone.now()
    bulk_create_from_df(
        EntityName,
        names,
        ["entity_id", "type", "value", "lang", "registry_id", "date_created"],
    )
    logger.info(f"Generated {len(names)} aliases from {REGISTRY_ROR}.")


def update_entity_raw_logo_url(
    data: pd.DataFrame, date_update: datetime | None = None
):
    """
    Update the `raw_logo_url` of the given Entities.
    It requires the columns id, raw_logo_url
    """
    if date_update is None:
        date_update = datetime.now(UTC)
    data["date_last_updated"] = date_update
    bulk_update_from_df(
        Entity, data, ["id", "raw_logo_url", "date_last_updated"]
    )


def ingest_extra_logo_urls(file_path: str | None = None):
    """
    Ingest static known raw_logo_url from a formatted CSV input file.
    """
    if file_path is None:
        file_path = str(
            app_settings.TSOSI_APP_DATA_DIR
            / "assets"
            / "wikidata_extra_logo_urls.csv"
        )
    logger.info(f"Ingesting extra logo URLs from file {file_path}")
    try:
        data = pd.read_csv(file_path)
    except Exception as e:
        logger.error(
            f"Failed to load logo_url file with path `{file_path}` - "
            f"Original exception: {e}"
        )
        return

    data = (
        data[~data["logo"].isna()]
        .drop_duplicates("wiki_id")
        .rename(columns={"logo": "raw_logo_url"})
    )
    data["wiki_id"] = data["wiki_id"].str.strip()

    # Get the identifier_id <-> entity_id mapping
    identifiers = Identifier.objects.filter(
        value__in=data["wiki_id"].to_list(), entity__isnull=False
    ).values_list("value", "entity_id")
    if len(identifiers) == 0:
        return
    mapping = pd.DataFrame(list(identifiers), columns=["identifier_id", "id"])

    results = data.merge(
        mapping, how="inner", left_on="wiki_id", right_on="identifier_id"
    )[["id", "raw_logo_url"]].drop_duplicates("id")
    if results.empty:
        return

    update_entity_raw_logo_url(results)
    logger.info(f"Updated {len(results)} entity `raw_logo_url`.")
