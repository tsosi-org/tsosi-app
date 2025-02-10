import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from tsosi.data.exceptions import DataException
from tsosi.models import (
    Currency,
    DataLoadSource,
    Entity,
    Identifier,
    IdentifierEntityMatching,
    Transfert,
    TransfertEntityMatching,
)
from tsosi.models.identifier import MATCH_CRITERIA_FROM_INPUT
from tsosi.models.static_data import (
    REGISTRY_ROR,
    REGISTRY_WIKIDATA,
    fill_static_data,
)
from tsosi.models.transfert import (
    MATCH_CRITERIA_NEW_ENTITY,
    TRANSFERT_ENTITY_TYPE_AGENT,
    TRANSFERT_ENTITY_TYPE_EMITTER,
    TRANSFERT_ENTITY_TYPE_RECIPIENT,
)
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC, MATCH_SOURCE_MANUAL

from .currencies.currency_rates import insert_currencies
from .db_utils import (
    IDENTIFIER_CREATE_FIELDS,
    IDENTIFIER_MATCHING_CREATE_FIELDS,
    bulk_create_from_df,
)
from .entity_matching import match_entities, matchable_entities
from .preparation import raw_data_config as dc
from .signals import identifiers_created, transferts_created
from .transfert_matching import flag_duplicate_transferts
from .utils import drop_duplicates_keep_index

logger = logging.getLogger(__name__)

TRANSFERT_ENTITY_TYPE = "transfert_entity_type"
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
        #     to_match[TRANSFERT_ENTITY_TYPE] == TRANSFERT_ENTITY_TYPE_AGENT
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
        match_entities(to_match, base_entities, True)
        for col in match_columns:
            entities.loc[to_match.index, col] = to_match[col]


def entities_to_create(entities: pd.DataFrame) -> pd.DataFrame:
    """
    Get distinct entities according to the matching rules.
    Add a reference to the entity to be created in `entity_to_create_id`,
    referring to its index in the resulting DataFrame.

    :param entities:    The entity data, as a dataframe. It must contain
                        the columns `name`, `country`, `website`, `ror_id`,
                        `wikidata_id`, `is_matchable`
    :returns:           The grouped entities, as a dataframe.
    """
    df_to_concat = []
    mandatory_columns = [
        "name",
        "country",
        "website",
        "ror_id",
        "wikidata_id",
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
    pid_columns = ["ror_id", "wikidata_id"]
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


def extract_entities(transferts: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the entity data into a brand new dataframe with references
    to the original indexes.
    """
    emitters_cols_mapping = {
        dc.FieldEmitterName.NAME: "name",
        dc.FieldEmitterCountry.NAME: "country",
        dc.FieldEmitterUrl.NAME: "website",
        dc.FieldEmitterRorId.NAME: "ror_id",
        dc.FieldEmitterWikidataId.NAME: "wikidata_id",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = ~transferts[dc.FieldEmitterName.NAME].isnull()
    emitters = transferts[mask][emitters_cols_mapping.keys()].rename(
        columns=emitters_cols_mapping
    )
    emitters[TRANSFERT_ENTITY_TYPE] = TRANSFERT_ENTITY_TYPE_EMITTER

    recipient_cols_mapping = {
        dc.FieldRecipientName.NAME: "name",
        dc.FieldRecipientCountry.NAME: "country",
        dc.FieldRecipientUrl.NAME: "website",
        dc.FieldRecipientRorId.NAME: "ror_id",
        dc.FieldRecipientWikidataId.NAME: "wikidata_id",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = ~transferts[dc.FieldRecipientName.NAME].isnull()
    recipients = transferts[mask][recipient_cols_mapping.keys()].rename(
        columns=recipient_cols_mapping
    )
    recipients[TRANSFERT_ENTITY_TYPE] = TRANSFERT_ENTITY_TYPE_RECIPIENT

    agent_cols_mapping = {
        dc.FieldAgentName.NAME: "name",
        dc.FieldAgentCountry.NAME: "country",
        dc.FieldAgentUrl.NAME: "website",
        dc.FieldAgentRorId.NAME: "ror_id",
        dc.FieldAgentWikidataId.NAME: "wikidata_id",
        dc.FieldOriginalId.NAME: "original_id",
    }
    mask = transferts[dc.FieldAgentName.NAME].isnull()
    agents = transferts[~mask][agent_cols_mapping.keys()].rename(
        columns=agent_cols_mapping
    )
    agents[TRANSFERT_ENTITY_TYPE] = TRANSFERT_ENTITY_TYPE_AGENT

    entities = pd.concat([emitters, recipients, agents], ignore_index=True)
    return entities


def create_identifiers(identifiers: pd.DataFrame, datetime: datetime):
    """
    Insert new Identifier and IdentifierEntityMatching records.
    """
    if len(identifiers) == 0:
        return

    identifiers["date_created"] = datetime
    identifiers["date_last_updated"] = datetime

    bulk_create_from_df(
        Identifier, identifiers, IDENTIFIER_CREATE_FIELDS, "identifier_id"
    )

    identifiers["date_start"] = datetime
    bulk_create_from_df(
        IdentifierEntityMatching, identifiers, IDENTIFIER_MATCHING_CREATE_FIELDS
    )
    logger.info(
        f"Created {len(identifiers)} Identifier and IdentifierEntityMatching records."
    )


def create_entities(entities: pd.DataFrame, datetime: datetime):
    """
    Insert new Entity records in the database.
    The IDs resulting from the insertion are appended to the input data.

    1 - Create an Entity record with given data. \\
    2 - If the entity has a referenced PID: \\
        2.a - Create an Identifier record \\
        2.b - Create an IdentifierEntityMatching record.

    :param entities:    The entities to be created.
    """
    entities["date_created"] = datetime
    entities["date_last_updated"] = datetime
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
    identifiers = pd.concat(
        [ror_identifiers, wikidata_identifiers], ignore_index=True
    )
    identifiers["match_source"] = MATCH_SOURCE_MANUAL
    identifiers["match_criteria"] = MATCH_CRITERIA_FROM_INPUT

    create_identifiers(identifiers, datetime)


def create_currencies(currencies: list[str], datetime: datetime):
    existing_currencies = [c.id for c in Currency.objects.all()]
    c_to_create = [c for c in currencies if c not in existing_currencies]
    for c in c_to_create:
        currency = Currency(
            id=c, name=c, date_created=datetime, date_last_updated=datetime
        )
        currency.save()


def create_transferts(transferts: pd.DataFrame, datetime: datetime):
    """
    Insert new Transfert records in the database.

    1 - Create a Transfert record with the given data.
    2 - Create a TransfertEntityMatching entry for every entity
        attached to the transfert.
    """
    transferts["date_created"] = datetime
    transferts["date_last_updated"] = datetime

    fields = [
        "raw_data",
        "emitter_id",
        "recipient_id",
        "agent_id",
        "amount",
        "currency_id",
        "date_invoice",
        "date_payment",
        "date_start",
        "date_end",
        "date_created",
        "date_last_updated",
        "original_id",
        "data_load_source_id",
        "hide_amount",
        "original_amount_field",
    ]
    bulk_create_from_df(Transfert, transferts, fields, "transfert_id")
    logger.info(f"Created {len(transferts)} Transfert records")


def create_transfert_entity_matching(
    transfert_entities: pd.DataFrame, datetime: datetime
):
    transfert_entities["date_created"] = datetime
    transfert_entities["date_last_updated"] = datetime

    fields = [
        "transfert_id",
        "transfert_entity_type",
        "entity_id",
        "match_criteria",
        "match_source",
        "comments",
        "date_created",
        "date_last_updated",
    ]
    bulk_create_from_df(TransfertEntityMatching, transfert_entities, fields)
    logger.info(
        f"Created {len(transfert_entities)} TransfertEntityMatching records"
    )


def get_data_load_source(source: dc.DataLoadSource):
    """
    Check the given data load validity.
    Return a fresh DataLoadSource instance.
    """
    try:
        query_args = {
            "data_source_id": source.data_source_id,
            "full_data": True,
        }
        if source.year:
            query_args["year"] = source.year

        source = DataLoadSource.objects.get(**query_args)
        raise DataException(
            f"A full data load with provided source ID {source.data_source_id} "
            f"and year {source.year} was already performed."
        )
    except ObjectDoesNotExist:
        source = DataLoadSource(**source.serialize())
    return source


@transaction.atomic
def ingest_new_records(
    transferts: pd.DataFrame,
    source: DataLoadSource,
    hide_amount: bool,
    send_signals: bool = True,
):
    """
    Insert the new records in the database and create appropriate relations.
    Expects the data to be in the appropriate format (ie. processed with
    `data_preparation.prepare_data`).

    1 - Pre-match entity with existing ones. \\
    2 - Create entities for the remaining ones. \\
    3 - Create transferts with FK to the above entities. \\
    4 - Create appropriate entries in TransfertEntityMatching.

    :param data:        Data formatted to TSOSI format, ie. using
                        `RawDataConfig.process` method.
    :param source:      The data load source to be appended to each transfert.
    :param hide_amount: Whether the transfert amounts should be hidden.
    """
    logger.info(f"Ingesting {len(transferts)} transfert records.")
    now = timezone.now()

    fill_static_data()

    # Set the data load source
    source.date_created = now
    source.date_last_updated = now
    source.save()
    transferts["data_load_source_id"] = source.pk
    transferts["hide_amount"] = hide_amount

    # Extract entities
    transfert_entities = extract_entities(transferts)
    transfert_entities["is_matchable"] = transfert_entities.apply(
        entity_is_matchable, axis=1
    )

    # TODO: Implement and use
    # When implemented, adjust accordingly the handling of existing entities
    # when mapping entities to transferts
    match_entities_with_db(transfert_entities)
    entity_null_mask = transfert_entities["entity_id"].isnull()

    entities_new = transfert_entities[entity_null_mask].copy()
    e_to_create = entities_to_create(entities_new)
    create_entities(e_to_create, now)

    # Map back the entity data to the transfert dataframe.
    # First complete the entites DF with the created Entity's ID.
    transfert_entities.loc[entities_new.index, "entity_id"] = entities_new[
        ENTITY_TO_CREATE_ID
    ].map(e_to_create["entity_id"])
    transfert_entities.loc[entities_new.index, "match_criteria"] = (
        MATCH_CRITERIA_NEW_ENTITY
    )

    # Map back every entity ID to their transfert
    for e_type in [
        TRANSFERT_ENTITY_TYPE_EMITTER,
        TRANSFERT_ENTITY_TYPE_RECIPIENT,
        TRANSFERT_ENTITY_TYPE_AGENT,
    ]:
        e_of_type = transfert_entities[
            transfert_entities[TRANSFERT_ENTITY_TYPE] == e_type
        ].set_index("original_id")["entity_id"]
        col_name = f"{e_type}_id"
        transferts[col_name] = transferts["original_id"].map(e_of_type)

    # Insert non-existing currencies
    currencies = (
        transferts[dc.FieldCurrency.NAME].drop_duplicates().dropna().to_list()
    )
    insert_currencies(currencies, now)
    transferts.rename(
        columns={dc.FieldCurrency.NAME: "currency_id"}, inplace=True
    )

    # Insert transferts
    create_transferts(transferts, now)

    # Insert TransfertEntityMatching
    transfert_entities["transfert_id"] = transfert_entities["original_id"].map(
        transferts.set_index("original_id")["transfert_id"]
    )
    transfert_entities["match_source"] = MATCH_SOURCE_AUTOMATIC
    create_transfert_entity_matching(transfert_entities, now)

    if send_signals:
        send_post_ingestion_signals()
    logger.info(f"Successfully ingested {len(transferts)} records.")


def ingest_data_file(file_path: str | Path, send_signals: bool = True) -> bool:
    """
    Ingest data from the given data file.
    The data file should have been generated with
    `RawDataConfig.generate_data_file`
    """
    logger.info(f"Ingesting data file {file_path}")
    with open(file_path, "r") as f:
        file_content = json.load(f)
    file_content["source"] = dc.DataLoadSource(**file_content["source"])
    ingestion_config = dc.DataIngestionConfig(**file_content)
    df = pd.DataFrame.from_records(ingestion_config.data)
    try:
        source = get_data_load_source(ingestion_config.source)
    except DataException as e:
        logger.info(f"Skipping ingestion of file {file_path}:\n{e}")
        return False
    # flag_duplicate_transferts(df, source)
    ingest_new_records(df, source, ingestion_config.hide_amount, send_signals)
    return True


def send_post_ingestion_signals():
    """
    Send signals to trigger post-ingestion pipeline.
    """
    registries = [REGISTRY_ROR, REGISTRY_WIKIDATA]
    transferts_created.send(None)
    identifiers_created.send(None, registries=registries)
