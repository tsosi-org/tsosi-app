import logging
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests
from django.core.exceptions import ImproperlyConfigured
from tsosi.app_settings import app_settings

from .entity_mapping import ENTITY_MAPPING

logger = logging.getLogger(__name__)

SCIPOST_TOKEN_URL = "https://scipost.org/o/token/"
# Do not write query params in below URLs
SCIPOST_SUBSIDY_API_URL = "https://scipost.org/api/private/subsidies/"
SCIPOST_PAYMENTS_API_URL = "https://scipost.org/api/private/subsidies/payments/"
SCIPOST_COLLECTIVES_API_URL = (
    "https://scipost.org/api/private/subsidies/collectives/"
)
# We use a 500 limit to perform only 1 or 2 queries. Beware as SciPost
# might de-activate this option
API_PARAMS = {"limit": 500, "format": "json"}


def get_entity_mapping() -> pd.DataFrame:
    """
    Get our custom entity mapping for SciPost
    """
    mapping = pd.DataFrame.from_records(ENTITY_MAPPING)
    mapping["_key"] = 1
    grouped = mapping.groupby("organization_id")["_key"].count().reset_index()
    duplicates = grouped[grouped["_key"] > 1]
    if not duplicates.empty:
        raise Exception(
            f"Duplicated matching entries for entities: {duplicates["organization_id"].to_list()}"
        )
    del mapping["_key"]
    return mapping


def get_trailing_url_path(s: pd.Series):
    """
    Get the last path value from an URL, series wise.
    """
    return (
        s.str.split("#")
        .str[0]
        .str.split("?")
        .str[0]
        .str.strip("/")
        .str.split("/")
        .str[-1]
    )


def exhaust_paginated_endpoint(
    url: str, headers: dict[str, str] = dict(), max_queries: int = 30
) -> list:
    """
    Query the given URL until all result pages have been received or
    the max number of queries is reached.
    It expects a paginated endpoint with a top-level `next` entry to fetch
    the next result page.
    """
    results_data = {
        "total": None,
        "total_received": 0,
        "data": [],
    }

    query_url = url
    query_number = 0

    while query_url is not None:
        assert (
            query_number <= max_queries
        ), f"ERROR - Reached max number of queries ({max_queries}) for endpoint {url}."

        resp = requests.get(query_url, headers=headers)
        if resp.status_code >= 300:
            raise Exception(
                f"SciPost endpoint HTTP resp `{resp.status_code}`\t"
                f"{str(resp.content)}"
            )

        data = resp.json()
        query_number += 1
        query_url = data["next"]

        assert "next" in data
        assert isinstance(
            data["results"], list
        ), "Error - API result 'results' key is not a list."

        if results_data["total"] is None:
            results_data["total"] = data["count"]

        assert (
            data["count"] == results_data["total"]
        ), "ERROR - Number of results has change throughout collection."

        results_data["total_received"] += len(data["results"])
        results_data["data"].extend(data["results"])

    assert (
        results_data["total_received"] == results_data["total"]
    ), "ERROR - Total number of received subsidies =! from the API count."

    return results_data["data"]


def get_scipost_token() -> str:
    """
    Retrieve an authentication token from SciPost to access the protected API.
    """
    logger.info("Collecting OAuth2 token")
    auth_data = app_settings.SCIPOST_AUTH

    if auth_data is None:
        raise ImproperlyConfigured(
            "You need to set the `TSOSI_SCIPOST_AUTH` "
            "setting to use SciPost API."
        )

    payload = {
        "grant_type": "password",
        "username": auth_data["username"],
        "password": auth_data["password"],
        "scope": "read",
    }
    auth = (auth_data["client_id"], auth_data["client_secret"])
    token_data: dict = requests.post(
        SCIPOST_TOKEN_URL, payload, auth=auth
    ).json()

    token = token_data.get("access_token")
    if token is None:
        raise Exception(
            "Error while getting SciPost access token. "
            f"Token endpoint response:\n{token_data}"
        )
    logger.info("Token obtained.")
    return token


def get_scipost_raw_data(
    dest_folder: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Retrieve all SciPost subsidy data from their API and dump it
    in the specified files.

    :param dest_folder: The path of the folder where the data should be written.
                        If `None`, the data is not exported.
                        Defaults to `None`.
    """
    logger.info("Collecting Scipost funding data...")

    token = get_scipost_token()

    headers = {"Authorization": f"Bearer {token}"}
    api_params = urlencode(API_PARAMS)
    today_str = str(date.today())

    endpoints = {
        "subsidies": {
            "url": SCIPOST_SUBSIDY_API_URL,
            "file_base": "scipost_subsidies",
        },
        "payments": {
            "url": SCIPOST_PAYMENTS_API_URL,
            "file_base": "scipost_payments",
        },
        "collectives": {
            "url": SCIPOST_COLLECTIVES_API_URL,
            "file_base": "scipost_collectives",
        },
    }

    results = {}
    for code, endpoint in endpoints.items():
        url = f"{endpoint["url"]}?{api_params}"
        data = exhaust_paginated_endpoint(url, headers)
        df = pd.DataFrame.from_records(data)

        logger.info(
            f"Collected all {endpoint["file_base"]} - {len(data)} entries"
        )

        if dest_folder:
            dest_file = (
                dest_folder / f"{today_str}_{endpoint["file_base"]}.json"
            )
            logger.info(f"Dumping data to file: {dest_file}")

            with open(dest_file, "w") as f:
                df.to_json(
                    f,
                    orient="records",
                    indent=2,
                )

        results[code] = df

    return results


COLS_OF_INTEREST = [
    "amount",
    "invoice_date",
    "payment_date",
    "status",
    "emitter",
    "emitter_type",
    "emitter_country",
    "emitter_ror_id",
    "subsidy_id",
    "subsidy_description",
    "subsidy_amount",
    "subsidy_amount_publicly_shown",
    "subsidy_url",
    "subsidy_type",
    "subsidy_status",
    "subsidy_date_from",
    "subsidy_date_until",
    "has_payment",
    "organization_url",
]


def prepare_payments(df: pd.DataFrame):
    subsidies = pd.json_normalize(df["subsidy"]).add_prefix(  # type: ignore
        "subsidy_"
    )
    data = pd.concat([df.drop(columns=["subsidy"]), subsidies], axis=1)
    data.rename(
        columns={
            "subsidy_organization.name": "emitter",
            "subsidy_organization.orgtype": "emitter_type",
            "subsidy_organization.country": "emitter_country",
            "subsidy_organization.ror_id": "emitter_ror_id",
            "subsidy_organization.url": "organization_url",
            "subsidy_subsidy_type": "subsidy_type",
        },
        inplace=True,
    )
    data["has_payment"] = True

    cols_of_interest = [c for c in COLS_OF_INTEREST if c in data.columns]
    return data[cols_of_interest].copy()


def prepare_subsidies(df: pd.DataFrame):
    organizations = pd.json_normalize(df["organization"]).add_prefix(  # type: ignore
        "organization_"
    )
    data = pd.concat(
        [
            df.drop(columns=["organization"]).add_prefix("subsidy_"),
            organizations,
        ],
        axis=1,
    )
    data.rename(
        columns={
            "organization_name": "emitter",
            "organization_orgtype": "emitter_type",
            "organization_country": "emitter_country",
            "organization_ror_id": "emitter_ror_id",
            "subsidy_amount_publicy_shown": "amount_publicly_shown",
        },
        inplace=True,
    )
    data["has_payment"] = False

    cols_of_interest = [c for c in COLS_OF_INTEREST if c in data.columns]
    return data[cols_of_interest].copy()


def prepare_collectives(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    organizations = pd.json_normalize(data["coordinator"]).add_prefix("organization_")  # type: ignore
    data = pd.concat(
        [
            data.drop(columns=["coordinator"]),
            organizations,
        ],
        axis=1,
    )
    data.rename(
        columns={
            "organization_name": "agent",
            "organization_orgtype": "agent_type",
            "organization_country": "agent_country",
            "organization_ror_id": "agent_ror_id",
        },
        inplace=True,
    )
    data["organization_id"] = get_trailing_url_path(
        data["organization_url"]
    ).astype(int)
    data["agent_wikidata_id"] = None
    data["agent_website_url"] = None

    # Merge custom mapping
    mapping = get_entity_mapping()
    data = data.merge(mapping, on="organization_id", how="left")
    data_no_ror = data["agent_ror_id"].isna()
    if data_no_ror.any():
        data.loc[data_no_ror, "agent_ror_id"] = data[data_no_ror]["ror_id"]
        data.loc[data_no_ror, "agent_wikidata_id"] = data[data_no_ror][
            "wikidata_id"
        ]
        data.loc[data_no_ror, "agent_website_url"] = data[data_no_ror][
            "website_url"
        ]

    # Explode subsidies
    exploded = data.explode("subsidies")
    exploded["subsidies"] = exploded["subsidies"].astype(int)

    # Check for duplicates
    exploded["_key"] = 1
    grouped = exploded.groupby("subsidies")["_key"].count().reset_index()
    duplicates = grouped[grouped["_key"] > 1]
    if not duplicates.empty:
        raise Exception(
            "Subsidies appearing in distinct collectives: "
            f"{duplicates["subsidies"].drop_duplicates().to_list()}"
        )
    del exploded["_key"]
    exploded.rename(columns={"subsidies": "subsidy_id"}, inplace=True)

    cols_of_interest = [
        "name",
        "description",
        "subsidy_id",
        "agent",
        "agent_type",
        "agent_country",
        "agent_ror_id",
        "agent_wikidata_id",
        "agent_website_url",
        "organization_id",
    ]
    return exploded[cols_of_interest].copy()


def prepare_data(
    payments: pd.DataFrame, subsidies: pd.DataFrame, collectives: pd.DataFrame
) -> pd.DataFrame:
    """
    Prepare SciPost consolidated transfer dataset from raw data.

    :param payments:    SciPost payments data.
    :param subsidies:   SciPost subsidies data.
    :param collectives: SciPost collectives data.
    """
    # Prepare payments dataframe
    payments_prepared = prepare_payments(payments)

    # Prepare subsidies dataframe
    subsidies_prepared = prepare_subsidies(subsidies)

    # Gather payments and subsidies without payments
    subsidies_missing = subsidies_prepared[
        ~subsidies_prepared["subsidy_url"].isin(
            payments_prepared["subsidy_url"]
        )
    ]
    data = pd.concat([payments_prepared, subsidies_missing], axis=0)

    # Compute useful data
    data["subsidy_id"] = get_trailing_url_path(data["subsidy_url"]).astype(int)
    data["subsidy_url"] = "https://scipost.org" + data["subsidy_url"]
    data["hide_amount"] = ~data["subsidy_amount_publicly_shown"]
    data["organization_id"] = get_trailing_url_path(
        data["organization_url"]
    ).astype(int)

    ## Filter dataset according to statuses
    # Keep rows where payment_status == "paid" OR subsidy_status == "received"
    mask_status = (data["subsidy_status"] == "received") | (
        data["status"] == "paid"
    )
    # Subsidies with non-null amount and no transfers must be kept. They usually
    # correspond to a subsidy paid by another entity.
    # Subsidies with 0-amount and non-null transfers must be discarded. They
    # correspond to an entity paying for others' subsidies;
    mask_null_subsidies_no_transfer = (data["subsidy_amount"] != 0) | (
        data["has_payment"] == False
    )

    filtered = data[mask_status & mask_null_subsidies_no_transfer].copy()

    # Fill amount column from the subsidy for missing transfers
    no_transfer = filtered["has_payment"] == False
    filtered.loc[no_transfer, "amount"] = filtered[no_transfer][
        "subsidy_amount"
    ]
    filtered.drop(
        columns=["subsidy_amount", "subsidy_status", "status", "has_payment"],
        inplace=True,
    )

    # Merge custom mapping
    filtered["emitter_wikidata_id"] = None
    filtered["emitter_website_url"] = None
    mapping = get_entity_mapping()
    mapping["_emitter_custom_mapping"] = 1

    filtered = filtered.merge(mapping, on="organization_id", how="left")
    filtered_no_ror = filtered["emitter_ror_id"].isna()
    if filtered_no_ror.any():
        filtered.loc[filtered_no_ror, "emitter_match_source"] = "manual"
        filtered.loc[filtered_no_ror, "emitter_ror_id"] = filtered[
            filtered_no_ror
        ]["ror_id"]
        filtered.loc[filtered_no_ror, "emitter_wikidata_id"] = filtered[
            filtered_no_ror
        ]["wikidata_id"]
        filtered.loc[filtered_no_ror, "emitter_website_url"] = filtered[
            filtered_no_ror
        ]["website_url"]
        filtered.drop(
            columns=[
                "ror_id",
                "wikidata_id",
                "website_url",
                "_emitter_custom_mapping",
            ],
            inplace=True,
        )

    # Log the organization with no enrichment data
    mask = (
        filtered["emitter_ror_id"].isna()
        & filtered["emitter_wikidata_id"].isna()
        & filtered["emitter_website_url"].isna()
    )
    no_info = filtered[mask]
    if not no_info.empty:
        msg = (
            "The following organizations have no PID nor "
            "a manual matching entry\t"
        )
        data = (
            no_info[["organization_id", "emitter"]]
            .drop_duplicates()
            .to_dict(orient="records")
        )
        msg += ", ".join(
            [
                (
                    "{ "
                    f"organization_id: {d["organization_id"]} - {d["emitter"]}"
                    " }"
                )
                for d in data
            ]
        )
        logger.warning(msg)

    # Add collective data
    collectives_prepared = prepare_collectives(collectives)
    results = filtered.merge(
        collectives_prepared[
            [
                "subsidy_id",
                "agent",
                "agent_type",
                "agent_country",
                "agent_ror_id",
                "agent_wikidata_id",
                "agent_website_url",
            ]
        ],
        how="left",
        on="subsidy_id",
    )
    return results
