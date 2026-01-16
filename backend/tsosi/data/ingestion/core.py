import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from tsosi.data.currencies.currency_rates import insert_currencies
from tsosi.data.db_utils import (
    IDENTIFIER_CREATE_FIELDS,
    IDENTIFIER_MATCHING_CREATE_FIELDS,
    bulk_create_from_df,
)
from tsosi.data.exceptions import DataException
from tsosi.data.preparation import raw_data_config as dc
from tsosi.data.signals import identifiers_created, transfers_created
from tsosi.data.utils import drop_duplicates_keep_index
from tsosi.models import (
    Currency,
    DataLoadSource,
    Entity,
    Identifier,
    IdentifierEntityMatching,
    Transfer,
    TransferEntityMatching,
)
from tsosi.models.identifier import MATCH_CRITERIA_FROM_INPUT
from tsosi.models.static_data import (
    REGISTRY_CUSTOM,
    REGISTRY_ROR,
    REGISTRY_WIKIDATA,
    fill_static_data,
)
from tsosi.models.transfer import (
    MATCH_CRITERIA_NEW_ENTITY,
    TRANSFER_ENTITY_TYPE_AGENT,
    TRANSFER_ENTITY_TYPE_EMITTER,
    TRANSFER_ENTITY_TYPE_RECIPIENT,
)
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC, MATCH_SOURCE_MANUAL

from .entity_matching import match_entities, matchable_entities
from .transfer_matching import deduplicate_transfers

logger = logging.getLogger(__name__)

TRANSFER_ENTITY_TYPE = "transfer_entity_type"
ENTITY_TO_CREATE_ID = "entity_to_create_id"


def entity_is_matchable(row: pd.Series) -> bool:
    """
    Returns whether the given entity can be automatically matched or grouped.
    TODO: Define the rules of whether an entity is matchable or not.
    """
    return True


def match_entities_with_db(entities: pd.DataFrame):
    """
    Match the given entities to the existing ones in the database.

    This adds the column `entity_id` with the matched Entity record.

    The automatic matching can only be made with entities having
    `is_matchable=True` (both the new ones and the ones in DB).

    :param entities:    The entity data to match.
    """
    match_columns = ["entity_id", "match_criteria", "comments"]
    for col in match_columns:
        entities.loc[:, col] = None

    to_match = entities[entities["is_matchable"] == True].copy()
    base_entities = matchable_entities()

    if not to_match.empty and not base_entities.empty:

        ###### WARNING
        ###### This is not coherent with our way of centralizing
        ###### the entities in the Entity table.
        ###### What we can do is to match agent **without PID** only to
        ###### existing agents.
        # # Match Agents/Consortiums only with agents/consortium
        # to_match_agent_mask = (
        #     to_match[TRANSFER_ENTITY_TYPE] == TRANSFER_ENTITY_TYPE_AGENT
        # )
        # to_match_agents = to_match[to_match_agent_mask].copy()
        # base_agent_mask = base_entities["is_agent"] == True
        # base_agents = base_entities[base_agent_mask].copy()
        # if not to_match_agents.empty:
        #     match_entities(to_match_agents, base_agents, True)
        #     for col in match_columns:
        #         entities.loc[to_match_agents.index, col] = to_match_agents[col]

        # # Handle the other entities
        # to_match_others = to_match[~to_match_agent_mask].copy()
        # base_others = base_entities[~base_agent_mask].copy()
        # match_entities(to_match_others, base_others, True)
        # for col in match_columns:
        #     entities.loc[to_match_others.index, col] = to_match_others[col]
        match_entities(to_match, base_entities, use_merged_id=True)
        for col in match_columns:
            entities.loc[to_match.index, col] = to_match[col]


def entities_to_create(entities: pd.DataFrame) -> pd.DataFrame:
    """
    Get distinct entities according to the matching rules.
    Add a reference to the entity to be created in `entity_to_create_id`,
    referring to its index in the resulting DataFrame.

    :param entities:    The entity data, as a dataframe. It must contain
                        the columns `name`, `country`, `website`, `ror_id`,
                        `wikidata_id`, `custom_id`, `is_matchable`
    :returns:           The grouped entities, as a dataframe.
    """
    df_to_concat = []
    mandatory_columns = [
        "name",
        "country",
        "website",
        "ror_id",
        "wikidata_id",
        "custom_id",
        "is_matchable",
    ]
    for c in mandatory_columns:
        if not c in entities.columns:
            raise Exception(
                f"The column `{c}` is not present in the given DataFrame."
            )

    # Non-matchable entities must be created.
    matchable_mask = entities["is_matchable"]
    no_match = entities[~matchable_mask].copy(deep=True)
    no_match["entity_temp_ids"] = [[i] for i in no_match.index]
    df_to_concat.append(no_match)

    # Work with remaining entities
    df = entities[matchable_mask].copy(deep=True)

    # Get entity data
    pid_columns = ["ror_id", "wikidata_id", "custom_id"]
    for c in pid_columns:
        pid_df = drop_duplicates_keep_index(df, c, "entity_temp_ids")
        if pid_df.empty:
            continue
        df_to_concat.append(pid_df)
        # Update the working dataframe - Remove rows with treated PID type.
        df = df[df[c].isnull()]

    # Group the remaining entities according to defined rules.
    group_by_columns = ["name", "country"]
    remaining_df = drop_duplicates_keep_index(
        df, group_by_columns, "entity_temp_ids", dropna=False
    )
    if not remaining_df.empty:
        df_to_concat.append(remaining_df)

    result = pd.concat(df_to_concat, ignore_index=True)

    # Add a column to the original dataframe to store the temp_id of the
    # to be created Entity.
    mapping = (
        result["entity_temp_ids"]
        .explode()
        .reset_index()
        .set_index("entity_temp_ids")
    )
    mapping.index.name = None
    entities[ENTITY_TO_CREATE_ID] = entities.index.map(mapping["index"])

    result.drop(columns="entity_temp_ids", inplace=True)
    return result


def extract_entities(transfers: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the entity data into a brand new dataframe with references
    to the input transfer's original ID.

    :param transfers:   The transfer dataframe.
    :returns entities:  The dataframe of all entity entries in the input
                        dataframe, with 1 row for each entity of each transfer.
    """
    emitters_cols_mapping = {
        dc.FieldEmitterName.NAME: "name",
        dc.FieldEmitterCountry.NAME: "country",
        dc.FieldEmitterUrl.NAME: "website",
        dc.FieldEmitterRorId.NAME: "ror_id",
        dc.FieldEmitterWikidataId.NAME: "wikidata_id",
        dc.FieldEmitterCustomId.NAME: "custom_id",
        dc.FieldEmitterSub.NAME: "sub_entity",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = ~transfers[dc.FieldEmitterName.NAME].isna()
    emitters = transfers[mask][emitters_cols_mapping.keys()].rename(
        columns=emitters_cols_mapping
    )
    emitters[TRANSFER_ENTITY_TYPE] = TRANSFER_ENTITY_TYPE_EMITTER

    recipient_cols_mapping = {
        dc.FieldRecipientName.NAME: "name",
        dc.FieldRecipientCountry.NAME: "country",
        dc.FieldRecipientUrl.NAME: "website",
        dc.FieldRecipientRorId.NAME: "ror_id",
        dc.FieldRecipientWikidataId.NAME: "wikidata_id",
        dc.FieldRecipientCustomId.NAME: "custom_id",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = ~transfers[dc.FieldRecipientName.NAME].isna()
    recipients = transfers[mask][recipient_cols_mapping.keys()].rename(
        columns=recipient_cols_mapping
    )
    recipients[TRANSFER_ENTITY_TYPE] = TRANSFER_ENTITY_TYPE_RECIPIENT

    agent_cols_mapping = {
        dc.FieldAgentName.NAME: "name",
        dc.FieldAgentCountry.NAME: "country",
        dc.FieldAgentUrl.NAME: "website",
        dc.FieldAgentRorId.NAME: "ror_id",
        dc.FieldAgentWikidataId.NAME: "wikidata_id",
        dc.FieldAgentCustomId.NAME: "custom_id",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = transfers[dc.FieldAgentName.NAME].isna()
    agents = transfers[~mask][agent_cols_mapping.keys()].rename(
        columns=agent_cols_mapping
    )
    agents[TRANSFER_ENTITY_TYPE] = TRANSFER_ENTITY_TYPE_AGENT

    entities = pd.concat([emitters, recipients, agents], ignore_index=True)
    return entities


def create_identifiers(identifiers: pd.DataFrame, date_stamp: datetime):
    """
    Insert new Identifier and IdentifierEntityMatching records.

    :param identifiers: The identifiers to create.
    :param date_stamp:  The datetime to use as the records' creation date.
    """
    if len(identifiers) == 0:
        return

    identifiers["date_created"] = date_stamp
    identifiers["date_last_updated"] = date_stamp

    bulk_create_from_df(
        Identifier, identifiers, IDENTIFIER_CREATE_FIELDS, "identifier_id"
    )

    identifiers["date_start"] = date_stamp
    bulk_create_from_df(
        IdentifierEntityMatching, identifiers, IDENTIFIER_MATCHING_CREATE_FIELDS
    )
    logger.info(
        f"Created {len(identifiers)} Identifier and IdentifierEntityMatching records."
    )


def create_entities(entities: pd.DataFrame, date_stamp: datetime):
    """
    Insert new Entity records in the database.
    The IDs resulting from the insertion are appended to the input data.
    
    Also insert attached Identifier records in the database.

    1 - Create an Entity record with given data. \\
    2 - If the entity has a referenced PID: \\
        2.a - Create an Identifier record \\
        2.b - Create an IdentifierEntityMatching record.

    :param entities:    The entities to create.
    :param date_stamp:  The datetime to use as the records' creation date.
    """
    entities["date_created"] = date_stamp
    entities["date_last_updated"] = date_stamp
    entities["raw_name"] = entities["name"]
    entities["raw_country"] = entities["country"]
    entities["raw_website"] = entities["website"]

    # Create Entity records
    fields = [
        "raw_name",
        "name",
        "raw_country",
        "country",
        "raw_website",
        "website",
        "is_matchable",
        "date_created",
        "date_last_updated",
    ]
    bulk_create_from_df(Entity, entities, fields, "entity_id")
    logger.info(f"Created {len(entities)} Entity records")

    # Create Identifier & IdentifierEntityMatching records
    ror_identifiers = (
        entities[~entities["ror_id"].isnull()][
            ["ror_id", "entity_id", "date_created", "date_last_updated"]
        ]
        .copy()
        .rename(columns={"ror_id": "value"})
    )

    ror_identifiers["registry_id"] = REGISTRY_ROR

    wikidata_identifiers = (
        entities[~entities["wikidata_id"].isnull()][
            ["wikidata_id", "entity_id", "date_created", "date_last_updated"]
        ]
        .copy()
        .rename(columns={"wikidata_id": "value"})
    )
    wikidata_identifiers["registry_id"] = REGISTRY_WIKIDATA

    custom_identifiers = (
        entities[~entities["custom_id"].isnull()][
            ["custom_id", "entity_id", "date_created", "date_last_updated"]
        ]
        .copy()
        .rename(columns={"custom_id": "value"})
    )
    custom_identifiers["registry_id"] = REGISTRY_CUSTOM

    identifiers = pd.concat(
        [ror_identifiers, wikidata_identifiers, custom_identifiers],
        ignore_index=True,
    )
    identifiers["match_source"] = MATCH_SOURCE_MANUAL
    identifiers["match_criteria"] = MATCH_CRITERIA_FROM_INPUT

    create_identifiers(identifiers, date_stamp)


def create_currencies(currencies: Iterable[str], date_stamp: datetime):
    """
    Utility to insert new Currency records in the database.

    :param currencies:  The currency ISO codes to create.
    :param date_stamp:  The datetime to use as the records' creation date.
    """
    existing_currencies = [c.id for c in Currency.objects.all()]
    c_to_create = [c for c in currencies if c not in existing_currencies]
    for c in c_to_create:
        currency = Currency(
            id=c, name=c, date_created=date_stamp, date_last_updated=date_stamp
        )
        currency.save()


def create_transfers(
    transfers: pd.DataFrame,
    data_load_source: DataLoadSource,
    date_stamp: datetime,
):
    """
    Utility to insert new Transfer records in the database.
    It's basically a list of the model fields to find in the dataframe.

    :param transfers:   The transfers to create.
    :param date_stamp:  The datetime to use as the records' creation date.
    """
    transfers["date_created"] = date_stamp
    transfers["date_last_updated"] = date_stamp

    fields = [
        "raw_data",
        "emitter_id",
        "recipient_id",
        "agent_id",
        "amount",
        "currency_id",
        "date_invoice",
        "date_payment_recipient",
        "date_payment_emitter",
        "date_start",
        "date_end",
        "date_created",
        "date_last_updated",
        "original_id",
        "hide_amount",
        "original_amount_field",
    ]
    bulk_create_from_df(Transfer, transfers, fields, "transfer_id")
    data_load_source.transfer_set.add(*transfers["transfer_id"].to_list())
    data_load_source.save()
    logger.info(f"Created {len(transfers)} Transfer records")


def create_transfer_entity_matching(
    transfer_entities: pd.DataFrame, date_stamp: datetime
):
    """
    Utility to insert new TransfertEntityMatching records in the database.
    It's basically a list of the model fields to find in the dataframe.

    :param transfers_entities:  The transfer <-> entity matching data to create.
    :param date_stamp:          The datetime to use as the records' creation date.
    """
    transfer_entities["date_created"] = date_stamp
    transfer_entities["date_last_updated"] = date_stamp

    fields = [
        "transfer_id",
        "transfer_entity_type",
        "entity_id",
        "sub_entity",
        "match_criteria",
        "match_source",
        "comments",
        "date_created",
        "date_last_updated",
    ]
    bulk_create_from_df(TransferEntityMatching, transfer_entities, fields)
    logger.info(
        f"Created {len(transfer_entities)} TransferEntityMatching records"
    )


def get_data_load_source(source: dc.DataLoadSource) -> DataLoadSource:
    """
    Check the given data load source validity.

    :param source:  The data load source config to check.
    :returns:       A fresh DataLoadSource model instance.
    """
    try:
        query_args = {
            "data_source_id": source.data_source_id,
            "full_data": True,
        }
        if source.year:
            query_args["year"] = source.year

        result = DataLoadSource.objects.get(**query_args)
        raise DataException(
            f"A full data load with provided source ID {source.data_source_id} "
            f"and year {source.year} was already performed."
        )
    except ObjectDoesNotExist:
        result = DataLoadSource(**source.serialize())
    return result


def validate_data_load_source(
    source: dc.DataLoadSource,
) -> tuple[bool, Sequence[DataLoadSource]]:
    """
    Return whether the given data load can be ingested, and the existing data
    loads it erases.

    :param source:      The data load to ingest.
    :returns valid:     Wheter it can be ingested.
    :retrurns oldies:   The existing data loads it should replace, ie. they
                        should be erased before ingesting the new one.
    """
    existing_loads = DataLoadSource.objects.filter(
        data_source_id=source.data_source_id
    )
    valid = True
    replaced = []

    # Full dataset to re-ingest
    if source.full_data and source.year is None:
        replaced = [r for r in existing_loads]
    # Full dataset for a given year
    elif source.full_data:
        for load in existing_loads:
            if load.full_data and load.year is None:
                valid = False
                replaced = []
                break
            elif load.year == source.year:
                replaced.append(load)
    # Partial dataset for a given year
    elif source.year is not None:
        for load in existing_loads:
            if load.full_data and load.year in [None, source.year]:
                valid = False
                break
    # Partial dataset without year
    else:
        for load in existing_loads:
            if load.full_data and load.year is None:
                valid = False
                break

    return valid, replaced


@transaction.atomic
def ingest_new_records(
    transfers: pd.DataFrame,
    source: DataLoadSource,
    send_signals: bool = True,
):
    """
    Insert the new records in the database and create appropriate relations.
    Expects the data to be in the appropriate format (ie. processed with
    `data_preparation.prepare_data`).

    1 - Pre-match entity with existing ones. \\
    2 - Create entities for the remaining ones. \\
    3 - Create transfers with FK to the above entities. \\
    4 - Create appropriate entries in TransferEntityMatching.

    :param transfers:       Tranfer data in TSOSI format, ie. prepared using
                            `RawDataConfig.prepare_data` method.
    :param source:          The data load source to be attached to each transfer.
    :param send_signals:    Whether to send `transfers_created` and
                            `identifiers_created` signals.
    """
    logger.info(f"Ingesting {len(transfers)} transfer records.")
    now = timezone.now()

    fill_static_data()

    # Set the data load source
    source.date_created = now
    source.date_last_updated = now
    source.save()

    # Extract entities
    transfer_entities = extract_entities(transfers)
    transfer_entities["is_matchable"] = transfer_entities.apply(
        entity_is_matchable, axis=1
    )

    # Match the input entities to the existing ones
    match_entities_with_db(transfer_entities)
    entity_null_mask = transfer_entities["entity_id"].isnull()

    # Create non-existing entities
    entities_new = transfer_entities[entity_null_mask].copy()
    e_to_create = entities_to_create(entities_new)
    create_entities(e_to_create, now)

    # Map back the entity data to the transfer dataframe.
    # First complete the entites DF with the created Entity's ID.
    transfer_entities.loc[entities_new.index, "entity_id"] = entities_new[
        ENTITY_TO_CREATE_ID
    ].map(e_to_create["entity_id"])
    transfer_entities.loc[entities_new.index, "match_criteria"] = (
        MATCH_CRITERIA_NEW_ENTITY
    )

    # Map back every entity ID to their transfer
    for e_type in [
        TRANSFER_ENTITY_TYPE_EMITTER,
        TRANSFER_ENTITY_TYPE_RECIPIENT,
        TRANSFER_ENTITY_TYPE_AGENT,
    ]:
        e_of_type = transfer_entities[
            transfer_entities[TRANSFER_ENTITY_TYPE] == e_type
        ].set_index("original_id")["entity_id"]
        col_name = f"{e_type}_id"
        transfers[col_name] = transfers["original_id"].map(e_of_type)

    # Insert non-existing currencies
    currencies = (
        transfers[dc.FieldCurrency.NAME].drop_duplicates().dropna().to_list()
    )
    insert_currencies(currencies, now)
    transfers.rename(
        columns={dc.FieldCurrency.NAME: "currency_id"}, inplace=True
    )

    # Create transfers
    create_transfers(transfers, source, now)

    # Insert TransferEntityMatching
    transfer_entities["transfer_id"] = transfer_entities["original_id"].map(
        transfers.set_index("original_id")["transfer_id"]
    )
    transfer_entities["match_source"] = MATCH_SOURCE_AUTOMATIC
    create_transfer_entity_matching(transfer_entities, now)

    if send_signals:
        send_post_ingestion_signals()
    logger.info(f"Successfully ingested {len(transfers)} records.")

    nb_merged = deduplicate_transfers(source)
    logger.info(
        f"Merged {nb_merged} transfers from data load source {source.data_load_name}"
    )


@transaction.atomic
def ingest(
    ingestion_config: dc.DataIngestionConfig, send_signals: bool = True
) -> bool:
    """
    Ingest data according to the given config.

    :param ingestion_config:    The ingestion config.
    :param send_signals:        Whether to send `transfers_created` and
                                `identifiers_created` signals.

    :returns:                   Whether the ingestion was performed.
    """
    logger.info(f"Ingesting data load: {ingestion_config.source.serialize()}")
    valid, oldies = validate_data_load_source(ingestion_config.source)
    if not valid:
        logger.info(
            "Skipping ingestion for data load "
            f"{ingestion_config.source.serialize()}"
        )
        return False

    # Delete old data loads
    if oldies:
        logger.info(
            "Removing the following old data loads: "
            f"{'\t'.join([d.serialize() for d in oldies])}"
        )
        transfers = Transfer.objects.filter(data_load_sources__in=oldies)
        connected_sources = (
            Transfer.objects.filter(merged_into__in=transfers)
            .values_list("data_load_sources", flat=True)
            .distinct()
        )
        transfers.delete()
        DataLoadSource.objects.filter(pk__in=[o.pk for o in oldies]).delete()
        nb_merged = 0
        for source in connected_sources:
            nb_merged += deduplicate_transfers(source)
        if nb_merged > 0:
            logger.info(
                f"Merged {nb_merged} transfers from connected data load sources."
            )

    df = pd.DataFrame.from_records(ingestion_config.data)
    dc.create_missing_fields(df)
    dls_config = ingestion_config.source.serialize()
    dls_entity_id = dls_config.pop("entity_id", None)
    source = DataLoadSource(**dls_config)

    ingest_new_records(df, source, send_signals)

    if dls_entity_id:
        entity = Identifier.objects.get(value=dls_entity_id).entity
        source.entity = entity
        source.save()

    return True


def ingest_data_file(file_path: str | Path, send_signals: bool = True) -> bool:
    """
    Ingest data from the given data file.
    The data file should have been generated with
    `RawDataConfig.generate_data_file`.

    :param file_path:       The Path object or string of the data file.
    :param send_signals:    Whether to send `transfers_created` and
                            `identifiers_created` signals.
    :returns:               Whether the file has been ingested.
    """
    logger.info(f"Ingesting data file {file_path}")
    with open(file_path, "r") as f:
        file_content = json.load(f)
    file_content["source"] = dc.DataLoadSource(**file_content["source"])
    ingestion_config = dc.DataIngestionConfig(**file_content)
    result = ingest(ingestion_config, send_signals)
    return result


def send_post_ingestion_signals():
    """
    Send signals to trigger post-ingestion pipeline.
    """
    registries = [REGISTRY_ROR, REGISTRY_WIKIDATA]
    transfers_created.send(None)
    identifiers_created.send(None, registries=registries)
