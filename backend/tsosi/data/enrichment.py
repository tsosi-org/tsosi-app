import asyncio
import logging
from datetime import UTC, date, datetime
from urllib.parse import unquote

import pandas as pd
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import transaction
from django.db.models import Count, F, Max, Q, QuerySet
from django.utils import timezone
from tsosi.models import (
    Entity,
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

from .db_utils import (
    IDENTIFIER_CREATE_FIELDS,
    IDENTIFIER_MATCHING_CREATE_FIELDS,
    DateExtremas,
    bulk_create_from_df,
    bulk_update_from_df,
    date_extremas_from_queryset,
)
from .merging import merge_entities
from .pid_registry.ror import (
    ROR_EXTRACT_MAPPING,
    fetch_ror_records,
    ror_record_extractor,
)
from .pid_registry.wikidata import (
    WIKIDATA_EXTRACT_MAPPING,
    fetch_wikidata_records_data,
    fetch_wikimedia_files,
    fetch_wikipedia_page_extracts,
)
from .preparation.cleaning_utils import clean_url
from .signals import identifiers_created, identifiers_fetched
from .task_result import TaskResult
from .token_bucket import (
    ROR_TOKEN_BUCKET,
    WIKIDATA_TOKEN_BUCKET,
    WIKIMEDIA_TOKEN_BUCKET,
    WIKIPEDIA_TOKEN_BUCKET,
)
from .utils import chunk_df, clean_null_values

logger = logging.getLogger(__name__)


@transaction.atomic
def ingest_entity_identifier_relations(
    data: pd.DataFrame, registry_id: str, date_update: datetime
):
    """
    Ingest the given entity <-> identifier relations for the given registry.

    Logic:    
    0 - Drop duplicates tuples (PID, entity) in input.
        Check coherency for duplicated entities. \\
    1 - Get the existing (PID value, Entity) relations & drop duplicated
        tuples (PID, entity) between input & existing \\
    2 - Get duplicated entities between input & mapping. Detach the existing
        relations for those entities (a new one will be created).
        --then-> Update existing relations with detached identifiers. \\
    3 - Handle identifiers in input that exist but are not attached
        to any entity
        --then-> Update existing relations \\
    4 - Create all new PIDs not in the existing relations
        --then-> Update existing relations with new relations. \\
    5 - All remaining rows in input should be merged according to the existing
        relations, as all identifiers in input now exist and are attached
        to an entity.


    :param data:            The dataframe of entity - identifier relations.
                            It must contain the columns:
                                `entity_id`
                                `identifier_value`
                                `match_source`
                                `match_criteria`
    :param registry_id:     The ID of the considered PID registry.
    :param date_update:     The date to register as `date_last_updated`
    """

    ## Consistency check - duplicated entity_id in the input data.
    new_relations = data.drop_duplicates(
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
        raise Exception(
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
    ex_identifiers = Identifier.objects.filter(registry__id=registry_id).values(
        "id", "value", "entity_id"
    )
    existing_relations = (
        pd.DataFrame.from_records(ex_identifiers)
        .rename(columns={"value": "identifier_value", "id": "identifier_id"})
        .set_index("identifier_id")
    )
    existing_relations["entity_id"] = existing_relations["entity_id"].apply(str)
    existing_relations["relation"] = existing_relations.apply(
        lambda row: (row["entity_id"], row["identifier_value"]), axis=1
    )

    new_relations["relation"] = new_relations.apply(
        lambda row: (row["entity_id"], row["identifier_value"]), axis=1
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
        existing_relations["entity_id"].isnull()
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


def empty_identifiers(registry_id: str | None = None) -> pd.DataFrame:
    """
    Retrieve the Identifier records attached to an entity without version.
    """
    queryset = Identifier.objects.filter(
        entity__isnull=False, current_version__isnull=True
    )
    if registry_id is not None:
        queryset = queryset.filter(registry_id=registry_id)
    instances = queryset.values("id", "registry_id", "value")
    return pd.DataFrame.from_records(instances)


def check_identifier_version_conflict():
    """
    Flag whether two versions of an identifier are conflicted.
    """
    pass


@transaction.atomic
def fetch_empty_identifier_records(
    registry_id: str, use_tokens: bool = True
) -> TaskResult:
    """
    Fetch the registry's record of every Identifier without a version.
    """
    logger.info(
        f"Fetching emtpy identifier records for registry {registry_id}."
    )
    if registry_id == REGISTRY_ROR:
        func = fetch_ror_records
        token_bucket = ROR_TOKEN_BUCKET
    elif registry_id == REGISTRY_WIKIDATA:
        func = fetch_wikidata_records_data
        token_bucket = WIKIDATA_TOKEN_BUCKET
    else:
        logger.error(f"Unkwown identifier registry {registry_id}")
        raise ValueError(f"Unknown identifier registry {registry_id}")

    result = TaskResult(partial=False, countdown=token_bucket.refill_period)
    identifiers = empty_identifiers(registry_id)
    if use_tokens:
        identifiers, result.partial = token_bucket.consume_for_df(identifiers)
    if identifiers.empty:
        logger.info(
            f"There are no empty identifiers for registry {registry_id}."
        )
        return result

    records = asyncio.run(func(identifiers["value"]))
    records = records if records.empty else records[records["error"] == False]
    result.partial = result.partial or len(records) != len(identifiers)
    if records.empty:
        logger.info(f"No identifier fetched for registry {registry_id}.")
        return result

    identifiers["record"] = identifiers["value"].map(
        records.set_index("id")["record"]
    )

    # Create IdentifierVersion
    identifier_versions = identifiers[~identifiers["record"].isnull()].copy()
    if identifier_versions.empty:
        logger.info(
            f"No records found for the queried {len(identifiers)} identifiers."
        )
        return result

    identifier_versions.rename(
        columns={
            "id": "identifier_id",
            "value": "identifier_value",
            "record": "value",
        },
        inplace=True,
    )
    date_update = timezone.now()
    identifier_versions["date_start"] = date_update
    identifier_versions["date_created"] = date_update
    identifier_versions["date_last_updated"] = date_update
    identifier_versions["date_last_fetched"] = date_update

    fields = [
        "identifier_id",
        "value",
        "date_start",
        "date_last_fetched",
        "date_created",
        "date_last_updated",
    ]
    bulk_create_from_df(
        IdentifierVersion, identifier_versions, fields, "identifier_version_id"
    )

    # Update identifiers' current_version
    cols_map = {
        "identifier_id": "id",
        "identifier_version_id": "current_version_id",
        "date_last_updated": "date_last_updated",
    }
    identifiers_for_udpate = identifier_versions.rename(columns=cols_map)
    bulk_update_from_df(Identifier, identifiers_for_udpate, cols_map.values())

    logger.info(
        f"Fetched {len(identifier_versions)} empty records "
        f"from registry {registry_id}"
    )
    identifiers_fetched.send(
        None, registry_id=registry_id, count=len(identifier_versions)
    )
    result.data_modified = True
    return result


def entities_with_identifier_data() -> pd.DataFrame:
    """
    Return the entities and associated identifier data.
    This dataset is used to update the Entity's calculated fields based
    on PID records.
    """
    entities = Entity.objects.filter(
        is_active=True, identifiers__isnull=False
    ).values(
        "id",
        # Raw values
        "raw_name",
        "raw_country",
        "raw_website",
        # Values to be clc
        "name",
        "country",
        "website",
        "wikipedia_url",
        "logo_url",
        "coordinates",
        "date_inception",
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

    ror_ids = identifiers[
        identifiers["registry_id"] == REGISTRY_ROR
    ].reset_index(drop=True)
    ror_extract = pd.json_normalize(
        ror_ids["record"].apply(ror_record_extractor), max_level=1
    )
    ror_ids = pd.concat([ror_ids, ror_extract], axis=1)
    ror_ids.drop(columns=["registry_id", "record"], inplace=True)
    entities = entities.merge(
        ror_ids.set_index("entity_id"),
        left_on="id",
        right_on="entity_id",
        how="left",
    )

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
        wikidata_ids.set_index("entity_id"),
        left_on="id",
        right_on="entity_id",
        how="left",
    )
    # Add missing columns, if any
    expected_cols = [
        *[f"ror_{name}" for name in ROR_EXTRACT_MAPPING.keys()],
        *[f"wikidata_{name}" for name in WIKIDATA_EXTRACT_MAPPING.values()],
    ]
    for col in expected_cols:
        if col in entities.columns:
            continue
        entities[col] = None

    url_cols = [
        "raw_website",
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
    """
    logger.info("Updating entity from PID records.")
    result = TaskResult(partial=False)

    entities = entities_with_identifier_data()
    if entities.empty:
        return result
    clean_null_values(entities)
    clc_field_priority = {
        "name": ["ror_name", "wikidata_name", "raw_name"],
        "country": ["ror_country", "wikidata_country", "raw_country"],
        "website": ["ror_website", "wikidata_website", "raw_website"],
        "logo_url": ["wikidata_logo_url"],
        "wikipedia_url": ["wikidata_wikipedia_url", "ror_wikipedia_url"],
        "coordinates": ["ror_coordinates", "wikidata_coordinates"],
        "date_inception": ["ror_date_inception", "wikidata_date_inception"],
    }
    # Compute the value for each field and check if there's a diff with existing
    # data
    for field, f_list in clc_field_priority.items():
        f_clc = f"{field}_clc"
        entities[f_clc] = entities[f_list].bfill(axis=1).iloc[:, 0]
        f_diff = f"{field}_diff"
        entities[f_diff] = ~entities[field].eq(entities[f_clc])

    # Select entities with new data to be updated
    entities["diff"] = entities[
        [f"{f}_diff" for f in clc_field_priority.keys()]
    ].any(axis=1)
    cols = ["id", *[f"{f}_clc" for f in clc_field_priority.keys()]]
    entities_to_update = entities[entities["diff"]][cols].copy()
    entities_to_update.rename(
        columns={f"{f}_clc": f for f in clc_field_priority.keys()}, inplace=True
    )
    entities_to_update["date_last_updated"] = timezone.now()
    cols = entities_to_update.columns.to_list()

    bulk_update_from_df(Entity, entities_to_update, cols)

    logger.info(
        f"Updated {len(entities_to_update)} Entity record from PID data."
    )
    result.data_modified = True
    return result


def new_identifiers_from_records() -> TaskResult:
    """
    Retrieve and ingest new entity <-> identifier relationships from PID data.
    """
    logger.info("Creating new identifiers from existing records.")
    result = TaskResult(partial=False)

    entities = entities_with_identifier_data()
    if entities.empty:
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

    ## Check for PID coherency
    # Mismatching ROR ID
    ror_check = entities.copy()
    ror_check["ror_doublon"] = ~(
        ror_check["ror_id"].isnull() | ror_check["wikidata_ror_id"].isnull()
    )
    ror_check["ror_id_diff"] = ~ror_check["ror_id"].eq(
        ror_check["wikidata_ror_id"]
    )

    mismatching_rors = ror_check[
        ror_check["ror_doublon"] & ror_check["ror_id_diff"]
    ]
    if not mismatching_rors.empty:
        msgs = []
        msgs.append(
            "The following entities have mismatching ROR ID from Wikidata:"
        )

        for _, row in mismatching_rors.iterrows():
            msgs.append(
                f"Entity: {row["name"]} -- "
                f"ROR ID: {row["ror_id"]} -- "
                f"Wiki ROR ID: {row["wikidata_ror_id"]}"
            )
        logger.warning("\n".join(msgs))
        entities.drop(mismatching_rors.index, inplace=True)

    # Mismatching Wikidata ID
    wiki_check = entities.copy()
    wiki_check["wiki_doublon"] = ~(
        entities["wikidata_id"].isnull() | entities["ror_wikidata_id"].isnull()
    )
    wiki_check["wiki_id_diff"] = ~wiki_check["wikidata_id"].eq(
        wiki_check["ror_wikidata_id"]
    )

    mismatching_wikis = wiki_check[
        wiki_check["wiki_doublon"] & wiki_check["wiki_id_diff"]
    ]
    if not mismatching_wikis.empty:
        msg = (
            "The following entities have mismatching Wikidata ID " "from ROR:\n"
        )
        for ind, row in mismatching_wikis.iterrows():
            msg += (
                f"Entity: {row["name"]} -- "
                f"Wikidata ID: {row["wikidata_id"]} -- "
                f"ROR Wikid ID: {row["ror_wikidata_id"]}"
            )
        logger.warning(msg)
        entities.drop(mismatching_wikis.index, inplace=True)

    if entities.empty:
        return result

    # Build new relations to ingest
    new_identifier_registries = []
    now = timezone.now()
    entities["new_ror"] = (
        entities["ror_id"].isnull() & ~entities["wikidata_ror_id"].isnull()
    )
    ror_rels = entities[entities["new_ror"]][
        ["id", "wikidata_ror_id"]
    ].reset_index(drop=True)
    if not ror_rels.empty:
        ror_rels.rename(
            columns={"id": "entity_id", "wikidata_ror_id": "identifier_value"},
            inplace=True,
        )
        ror_rels["match_source"] = MATCH_SOURCE_AUTOMATIC
        ror_rels["match_criteria"] = MATCH_CRITERIA_FROM_WIKIDATA
        ingest_entity_identifier_relations(ror_rels, REGISTRY_ROR, now)
        result.data_modified = True
        new_identifier_registries.append(REGISTRY_ROR)

    entities["new_wikidata"] = (
        entities["wikidata_id"].isnull() & ~entities["ror_wikidata_id"].isnull()
    )
    wikidata_rels = entities[entities["new_wikidata"]][
        ["id", "ror_wikidata_id"]
    ].reset_index(drop=True)
    if not wikidata_rels.empty:
        wikidata_rels.rename(
            columns={"ror_wikidata_id": "identifier_value", "id": "entity_id"},
            inplace=True,
        )
        wikidata_rels["match_source"] = MATCH_SOURCE_AUTOMATIC
        wikidata_rels["match_criteria"] = MATCH_CRITERIA_FROM_ROR
        ingest_entity_identifier_relations(
            wikidata_rels, REGISTRY_WIKIDATA, now
        )
        result.data_modified = True
        new_identifier_registries.append(REGISTRY_WIKIDATA)

    identifiers_created.send(None, registries=new_identifier_registries)
    return result


def update_null_wikipedia_url(date_update: datetime) -> None:
    """
    Reset wikipedia_extract & date_wikipedia_fetched for entities
    where wikipedia_url is null.
    """
    Entity.objects.filter(
        wikipedia_url__isnull=True, wikipedia_extract__isnull=False
    ).update(
        wikipedia_extract=None,
        date_last_updated=date_update,
        date_wikipedia_fetched=None,
    )


WIKIPEDIA_DATE_THRESHOLD_DAYS = 7


def entities_for_wikipedia_extract_update() -> pd.DataFrame:
    """
    Gets the entities for which the wikipedia extract must be updated.

    :returns:   The Dataframe with columns `id`, `wikipedia_url`,
                `wikipedia_extract`
    """
    date_value = timezone.now() - timezone.timedelta(
        days=WIKIPEDIA_DATE_THRESHOLD_DAYS
    )
    date_condition = Q(date_wikipedia_fetched__isnull=True) | Q(
        date_wikipedia_fetched__lt=date_value
    )
    instances = (
        Entity.objects.filter(is_active=True, wikipedia_url__isnull=False)
        .filter(date_condition)
        .values("id", "wikipedia_url", "wikipedia_extract")
    )
    df = pd.DataFrame.from_records(instances)
    if df.empty:
        return df
    # We only want wikipedia extract for entities with URL to the english wiki
    mask = df["wikipedia_url"].str.startswith("https://en.wikipedia.org")
    return df[mask].reset_index(drop=True)


def update_wikipedia_extract(use_tokens: bool = True) -> TaskResult:
    """
    Update the wikipedia extract of entities having a `wikipedia_url`.
    """
    logger.info("Updating wikipedia extracts.")
    result = TaskResult(
        partial=False, countdown=WIKIPEDIA_TOKEN_BUCKET.refill_period
    )

    entities = entities_for_wikipedia_extract_update()
    if use_tokens:
        entities, result.partial = WIKIPEDIA_TOKEN_BUCKET.consume_for_df(
            entities
        )
    if entities.empty:
        logger.info("No wikipedia extract to fetch.")
        return result

    entities["wiki_page_title"] = entities["wikipedia_url"].apply(
        lambda x: x.split("/")[-1]
    )
    results = asyncio.run(
        fetch_wikipedia_page_extracts(
            entities["wiki_page_title"].drop_duplicates()
        )
    )
    extracts = results[~results["error"]]
    result.partial = result.partial or len(extracts) != len(results)
    if extracts.empty:
        logger.info("No extracts returned via the wikipedia API.")
        return result

    entities["extract_new"] = entities["wiki_page_title"].map(
        extracts.set_index("title")["extract"]
    )
    # Filters entities to update
    clean_null_values(entities)
    entities["extract_diff"] = ~entities["extract_new"].eq(
        entities["wikipedia_extract"]
    )
    mask = entities["extract_diff"] & (
        ~entities["extract_new"].isnull() | entities["wiki_page_title"].isnull()
    )
    to_update = entities[mask].copy()
    now = timezone.now()
    if not to_update.empty:
        to_update["date_last_updated"] = now
        to_update["date_wikipedia_fetched"] = now
        to_update.drop(
            columns=[
                "wiki_page_title",
                "wikipedia_extract",
                "extract_diff",
                "wikipedia_url",
            ],
            inplace=True,
        )
        to_update.rename(
            columns={"extract_new": "wikipedia_extract"}, inplace=True
        )
        cols = to_update.columns.to_list()

        bulk_update_from_df(Entity, to_update, cols)
        logger.info(f"Updated {len(to_update)} wikipedia description")

    update_null_wikipedia_url(now)
    return result


def entities_for_logo_update() -> QuerySet[Entity]:
    """
    Gets the entities for which the logo must be updated.
    """
    date_value = timezone.now() - timezone.timedelta(
        days=WIKIPEDIA_DATE_THRESHOLD_DAYS
    )
    date_condition = Q(date_logo_fetched__isnull=True) | Q(
        date_logo_fetched__lt=date_value
    )
    return (
        Entity.objects.filter(logo_url__isnull=False, is_active=True)
        .filter(date_condition)
        .order_by("logo_url")
    )


def update_null_logo_url(date_update: datetime | None):
    """
    Reset logo & date_logo_fetched for entities where logo_url is null.
    """
    date_update = date_update if date_update is not None else timezone.now()
    instances = Entity.objects.filter(
        logo_url__isnull=True, logo__isnull=False, manual_logo=False
    )
    for e in instances:
        e.logo.delete(save=True)
        e.date_last_updated = date_update
        e.date_logo_fetched = None
        e.save()


def update_entity_logo_file(row: pd.Series):
    """"""
    e: Entity = row["entity"]
    url = row.get("final_url", row["url"])
    date_update = row["date_last_updated"]
    file_name = unquote(url.split("/")[-1])
    file_content: bytes = row["file_bytes"]
    # Delete existing file, if any
    if e.logo:
        e.logo.delete(save=True)
    temp_file = TemporaryUploadedFile(
        name=file_name,
        content_type=f"image/{file_name.split(".")[-1]}",
        size=len(file_content),
        charset=None,
    )
    # Write temp file then save entity
    temp_file.open("wb")
    temp_file.write(file_content)
    e.logo = temp_file
    e.date_logo_fetched = date_update
    e.save()
    temp_file.close()


def update_logos(
    date_update: datetime | None = None, use_tokens: bool = True
) -> TaskResult:
    """
    Download the logo files from wikimedia commons and store them locally.
    """
    logger.info("Downloading entity logo files from wikimedia commons.")
    result = TaskResult(
        partial=False, countdown=WIKIMEDIA_TOKEN_BUCKET.refill_period
    )

    instances = entities_for_logo_update()
    if len(instances) == 0:
        logger.info("No entity logo to update.")
        return result

    entity_mapping = {e.id: e for e in instances}

    df = pd.DataFrame.from_records(
        [{"id": i.id, "logo_url": i.logo_url} for i in instances]
    )
    if use_tokens:
        df, result.partial = WIKIMEDIA_TOKEN_BUCKET.consume_for_df(df)

    date_update = date_update if date_update is not None else timezone.now()
    updates = 0
    for chunk in chunk_df(df, 20):
        logo_results = asyncio.run(
            fetch_wikimedia_files(chunk["logo_url"].drop_duplicates())
        )
        chunk = chunk.merge(
            logo_results, left_on="logo_url", right_on="url", how="left"
        )
        chunk = chunk[~chunk["error"]]

        if chunk.empty:
            continue
        chunk["entity"] = chunk["id"].map(entity_mapping)
        chunk["date_last_updated"] = date_update
        chunk.apply(update_entity_logo_file, axis=1)
        updates += len(chunk)

    result.partial = result.partial or updates != len(df)
    result.data_modified = updates > 0
    logger.info(f"Downloaded {updates} entity logo files.")
    return result


def update_registry_data() -> TaskResult:
    """
    TODO: Routine to work with the external registry data.
    1 - For every active identifiers, fetch the record and compare with
        current version.
    2 - Create new version if required and flag whether
        the IdentifierEntityMatching should be reviewed.
    3 - Populate/update the clc field at the entity level from the records data:
        a - Name
        b - Country
        c - Url
        d - Logo
        e - Wikipedia extract
    """
    pass


def update_transfer_date_clc(
    instances: QuerySet[Transfer] | None = None,
):
    """
    Update the `date_clc` field for transfers based on the various
    date fields.
    """
    logger.info("Updating transfer CLC date.")
    if instances is None:
        instances = Transfer.objects.all().values(
            "id", "date_invoice", "date_payment", "date_start"
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
        data[["date_payment", "date_invoice", "date_start"]]
        .bfill(axis=1)
        .iloc[:, 0]
    )
    data["date_last_updated"] = timezone.now()
    columns = ["id", "date_clc", "date_last_updated"]
    bulk_update_from_df(Transfer, data, columns)


def update_entity_roles_clc():
    """
    Update the `is_emitter`, `is_recipient`, `is_agent` booleans according
    to the transfer data.
    """
    logger.info("Updating entity roles.")

    transfer_cols = [f"{t}_id" for t in TRANSFER_ENTITY_TYPES]
    transfers = pd.DataFrame.from_records(
        Transfer.objects.all().values("id", *transfer_cols)
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
        Transfer.objects.all(), ["date_clc"], groupby=["recipient_id"]
    )
    dates: dict[str, DateExtremas] = {
        d["recipient_id"]: d["_extremas"] for d in dates
    }

    total_transfers = Count("transfer_as_recipient")
    date_source_max = Max(
        "transfer_as_recipient__data_load_source__date_data_obtained"
    )

    entities = (
        Entity.objects.filter(is_recipient=True)
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
                "data_data_start",
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
