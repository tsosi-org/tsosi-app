"""
Tasks involving external API requests.
"""

import asyncio
import io
import logging
from datetime import datetime, timedelta
from urllib.parse import unquote

import pandas as pd
from django.core.files.images import ImageFile
from django.db import transaction
from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone
from tsosi.app_settings import app_settings
from tsosi.data.db_utils import bulk_create_from_df, bulk_update_from_df
from tsosi.data.pid_registry.ror import fetch_ror_records
from tsosi.data.pid_registry.wikidata import (
    fetch_wikidata_records_data,
    fetch_wikimedia_files,
    fetch_wikipedia_page_extracts,
)
from tsosi.data.signals import identifiers_fetched
from tsosi.data.task_result import TaskResult
from tsosi.data.token_bucket import (
    ROR_TOKEN_BUCKET,
    WIKIDATA_TOKEN_BUCKET,
    WIKIMEDIA_TOKEN_BUCKET,
    WIKIPEDIA_TOKEN_BUCKET,
)
from tsosi.data.utils import chunk_df, clean_null_values
from tsosi.models import (
    Entity,
    EntityRequest,
    Identifier,
    IdentifierRequest,
    IdentifierVersion,
)
from tsosi.models.entity import (
    ENTITY_REQUEST_WIKIMEDIA_LOGO,
    ENTITY_REQUEST_WIKIPEDIA_EXTRACT,
)
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

logger = logging.getLogger(__name__)


#### Identifier records fetching
def log_identifier_requests(results: pd.DataFrame):
    """
    Log the identifier request results in the `IdentifierRequest` table.

    :param results:     The DataFrame of identifier request results with
                        appropriate columns.
    """
    bulk_create_from_df(
        IdentifierRequest,
        results,
        [
            "identifier_id",
            "info",
            "timestamp",
            "http_status",
            "error",
            "error_msg",
        ],
    )


## Empty identifiers
def empty_identifiers(
    registry_id: str | None = None,
    query_threshold: int | None = None,
) -> pd.DataFrame:
    """
    Retrieve the Identifier records attached to an entity without version.

    :param registry_id:     Optional registry ID used to filter the identifiers.
    :param query_threshold: If not-null, filter out the identifiers with more
                            entries in the IdentifierRequest than the threshold
                            over the `IDENTIFIER_FETCH_DAYS` setting
    """
    queryset = Identifier.objects.filter(
        entity__isnull=False, current_version__isnull=True
    )
    if registry_id is not None:
        queryset = queryset.filter(registry_id=registry_id)

    if query_threshold is None:
        query_threshold = app_settings.IDENTIFIER_FETCH_RETRY
    time_threshold = timezone.now() - timedelta(
        days=app_settings.IDENTIFIER_FETCH_DAYS
    )
    queryset = queryset.annotate(
        request_nb=Count(
            "requests", filter=Q(requests__timestamp__gt=time_threshold)
        )
    ).filter(request_nb__lt=query_threshold)

    instances = queryset.values("id", "registry_id", "value")
    return pd.DataFrame.from_records(instances)


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
        if result.partial:
            logger.info(
                f"Bucket exhausted for registry {registry_id}. Retry later."
            )
        logger.info(
            f"There are no empty identifiers for registry {registry_id}."
        )
        return result

    records = asyncio.run(func(identifiers["value"]))

    # Log API requests
    id_requests = records.copy()
    id_requests["identifier_id"] = id_requests["id"].map(
        identifiers.set_index("value")["id"]
    )
    log_identifier_requests(id_requests)

    # Process results
    records = records if records.empty else records[records["error"] == False]
    result.partial = result.partial or len(records) != len(identifiers)
    if records.empty:
        logger.info(f"No identifier fetched for registry {registry_id}.")
        return result

    identifiers["record"] = identifiers["value"].map(
        records.set_index("id")["record"]
    )

    # Create IdentifierVersion
    identifier_versions = identifiers[~identifiers["record"].isna()].copy()
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


## Identifier refresh
def identifiers_for_refresh(
    registry_id: str | None = None, query_threshold: int | None = None
) -> pd.DataFrame:
    """
    Retrieve the Identifier records that need to be updated.

    :param registry_id:     Optional registry ID used to filter the identifiers.
    :param query_threshold: If not-null, filter out the identifiers with more
                            entries in the IdentifierRequest than the threshold
                            over the `IDENTIFIER_FETCH_DAYS` setting.
    """
    fetched_date_condition = timezone.now() - timezone.timedelta(
        days=app_settings.IDENTIFIER_REFRESH_DAYS
    )
    queryset = Identifier.objects.select_related("current_version").filter(
        entity__isnull=False,
        current_version__isnull=False,
        current_version__date_last_fetched__lt=fetched_date_condition,
    )
    if registry_id is not None:
        queryset = queryset.filter(registry_id=registry_id)

    if query_threshold is None:
        query_threshold = app_settings.IDENTIFIER_FETCH_RETRY
    time_threshold = timezone.now() - timedelta(
        days=app_settings.IDENTIFIER_FETCH_DAYS
    )
    queryset = queryset.annotate(
        request_nb=Count(
            "requests", filter=Q(requests__timestamp__gt=time_threshold)
        )
    ).filter(request_nb__lt=query_threshold)

    instances = queryset.values(
        "id",
        "registry_id",
        "value",
        "current_version_id",
        record=F("current_version__value"),
    )
    return pd.DataFrame.from_records(instances)


@transaction.atomic
def refresh_identifier_records(
    registry_id: str, use_tokens: bool = True
) -> TaskResult:
    """
    Routine to refresh the identifier records.

    TODO: Harmonize with `fetch_empty_identifier_records`. Most of the
    code is the same.

    1 - For every active identifiers, fetch the current record and compare with
        existing version.

    2 - Create a new version if the existing and new record differ.

    3 - Send the identifiers_fetched signal to trigger further processing.
    """
    logger.info(f"Refreshing identifier records for registry {registry_id}")
    if registry_id == REGISTRY_ROR:
        func = fetch_ror_records
        token_bucket = ROR_TOKEN_BUCKET
    elif registry_id == REGISTRY_WIKIDATA:
        func = fetch_wikidata_records_data
        token_bucket = WIKIDATA_TOKEN_BUCKET
    else:
        logger.error(f"Unknown identifier registry")
        raise ValueError(f"Unknown identifier registry {registry_id}")

    result = TaskResult(partial=False, countdown=token_bucket.refill_period)
    identifiers = identifiers_for_refresh(registry_id)
    if use_tokens:
        identifiers, result.partial = token_bucket.consume_for_df(identifiers)
    if identifiers.empty:
        if result.partial:
            logger.info(
                f"Bucket exhausted for registry {registry_id}. Retry later."
            )
        logger.info(
            f"There are no empty identifiers for registry {registry_id}."
        )
        return result

    records = asyncio.run(func(identifiers["value"]))

    # Log API requests
    id_requests = records.copy()
    id_requests["identifier_id"] = id_requests["id"].map(
        identifiers.set_index("value")["id"]
    )
    log_identifier_requests(id_requests)

    # Process results
    records = records if records.empty else records[records["error"] == False]
    result.partial = result.partial or len(records) != len(identifiers)
    if records.empty:
        logger.info(f"No records correctly fetched for registry {registry_id}.")
        return result

    identifiers["new_record"] = identifiers["value"].map(
        records.set_index("id")["record"]
    )
    # Discard the ones with empty record
    identifiers = identifiers[~identifiers["new_record"].isna()]

    identifiers["_diff"] = ~identifiers["record"].eq(identifiers["new_record"])

    no_change = identifiers[~identifiers["_diff"]][
        ["current_version_id"]
    ].copy()
    new_records = identifiers[identifiers["_diff"]].copy()
    del identifiers

    date_update = timezone.now()

    ## Handle un-changed records
    if not no_change.empty:
        no_change["date_last_updated"] = date_update
        no_change["date_last_fetched"] = date_update

        no_change.rename(columns={"current_version_id": "id"}, inplace=True)
        bulk_update_from_df(
            IdentifierVersion,
            no_change,
            ["id", "date_last_updated", "date_last_fetched"],
        )

    ## Handle modified records
    if new_records.empty:
        return result
    # Update old versions
    new_records["date_last_updated"] = date_update
    old_versions = new_records[
        ["current_version_id", "date_last_updated"]
    ].copy()
    old_versions["date_end"] = date_update
    old_versions.rename(columns={"current_version_id": "id"}, inplace=True)
    bulk_update_from_df(
        IdentifierVersion, old_versions, ["id", "date_end", "date_last_updated"]
    )

    # Create new versions
    new_versions = new_records[
        ["id", "new_record", "date_last_updated"]
    ].rename(
        columns={
            "id": "identifier_id",
            "new_record": "value",
        }
    )
    new_versions["date_created"] = date_update
    new_versions["date_start"] = date_update
    new_versions["date_last_fetched"] = date_update
    fields = [
        "identifier_id",
        "value",
        "date_start",
        "date_last_fetched",
        "date_created",
        "date_last_updated",
    ]
    bulk_create_from_df(
        IdentifierVersion, new_versions, fields, "identifier_version_id"
    )

    # Update identifier's current version
    cols_map = {
        "identifier_id": "id",
        "identifier_version_id": "current_version_id",
        "date_last_updated": "date_last_updated",
    }
    id_update = new_versions[cols_map.keys()].rename(columns=cols_map)
    bulk_update_from_df(Identifier, id_update, cols_map.values())

    logger.info(
        f"Updated {len(new_versions)} new identifier versions "
        f"for registry {registry_id}"
    )
    identifiers_fetched.send(
        None, registry_id=registry_id, count=len(new_versions)
    )
    result.data_modified = True
    return result


#### Wiki-related
def log_entity_requests(results: pd.DataFrame):
    """
    Log the request results in the `EntityRequest` table.

    :param results:     The DataFrame of API request results with appropriate
                        columns?
    """
    bulk_create_from_df(
        EntityRequest,
        results,
        [
            "entity_id",
            "type",
            "info",
            "timestamp",
            "http_status",
            "error",
            "error_msg",
        ],
    )


## Wikipedia extract fecthing
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


def entities_for_wikipedia_extract_update(
    query_threshold: int | None = None,
) -> pd.DataFrame:
    """
    Gets the entities for which the wikipedia extract must be updated.

    :returns:   The Dataframe with columns `id`, `wikipedia_url`,
                `wikipedia_extract`
    """
    queryset = Entity.objects.filter(
        is_active=True, wikipedia_url__isnull=False
    )

    # Last fetch condition
    date_value = timezone.now() - timezone.timedelta(
        days=app_settings.WIKI_REFRESH_DAYS
    )
    date_condition = Q(date_wikipedia_fetched__isnull=True) | Q(
        date_wikipedia_fetched__lt=date_value
    )
    queryset = queryset.filter(date_condition)

    # Number of attempts condition
    if query_threshold is None:
        query_threshold = app_settings.WIKI_FETCH_RETRY
    time_threshold = timezone.now() - timedelta(
        days=app_settings.WIKI_FETCH_DAYS
    )
    queryset = queryset.annotate(
        request_nb=Count(
            "requests",
            filter=Q(
                requests__timestamp__gt=time_threshold,
                requests__type=ENTITY_REQUEST_WIKIPEDIA_EXTRACT,
            ),
        )
    ).filter(request_nb__lt=query_threshold)

    # Query
    instances = queryset.values("id", "wikipedia_url", "wikipedia_extract")
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

    # Log the request results
    e_requests = results.copy()
    e_requests = entities[["id", "wiki_page_title"]].merge(
        results, how="left", left_on="wiki_page_title", right_on="title"
    )
    # Every row in entities should have a match in results
    # To be sure we fill the error if it's not
    no_res = e_requests["error"].isna()
    e_requests.loc[no_res, "error"] = True
    e_requests.loc[no_res, "error_msg"] = "No query was performed."
    e_requests["type"] = ENTITY_REQUEST_WIKIPEDIA_EXTRACT
    e_requests.rename(columns={"id": "entity_id"}, inplace=True)
    log_entity_requests(e_requests)

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


## Wikimedia logo fetching
def entities_for_logo_update(
    query_threshold: int | None = None,
) -> QuerySet[Entity]:
    """
    Gets the entities for which the logo must be updated.
    """
    queryset = Entity.objects.filter(logo_url__isnull=False, is_active=True)

    # Last fetch condition
    date_value = timezone.now() - timezone.timedelta(
        days=app_settings.WIKI_REFRESH_DAYS
    )
    date_condition = Q(date_logo_fetched__isnull=True) | Q(
        date_logo_fetched__lt=date_value
    )
    queryset = queryset.filter(date_condition)

    # Number of attempts condition
    if query_threshold is None:
        query_threshold = app_settings.WIKI_FETCH_RETRY
    time_threshold = timezone.now() - timedelta(
        days=app_settings.WIKI_FETCH_DAYS
    )
    queryset = queryset.annotate(
        request_nb=Count(
            "requests",
            filter=Q(
                requests__timestamp__gt=time_threshold,
                requests__type=ENTITY_REQUEST_WIKIMEDIA_LOGO,
            ),
        )
    ).filter(request_nb__lt=query_threshold)

    return queryset.order_by("logo_url")


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
    e.logo = ImageFile(io.BytesIO(file_content), name=file_name)
    e.date_logo_fetched = date_update
    e.save()


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
        # The discard of duplicates should occur before chunking...
        # There is usually no duplicates in this task.
        logo_results = asyncio.run(
            fetch_wikimedia_files(chunk["logo_url"].drop_duplicates())
        )
        chunk = chunk.merge(
            logo_results, left_on="logo_url", right_on="url", how="left"
        )

        # Log the requests
        logs = chunk.copy()
        no_res = logs["error"].isna()
        logs["type"] = ENTITY_REQUEST_WIKIMEDIA_LOGO
        logs.loc[no_res, "error"] = True
        logs.loc[no_res, "error_msg"] = "No query was performed."
        logs.rename(columns={"id": "entity_id"}, inplace=True)
        log_entity_requests(logs)

        # Process results
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
