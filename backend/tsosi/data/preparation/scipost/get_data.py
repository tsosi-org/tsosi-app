import json
import re
from datetime import date

import pandas as pd
import requests
from django.core.exceptions import ImproperlyConfigured
from tsosi.app_settings import app_settings

SCIPOST_TOKEN_URL = "https://scipost.org/o/token/"
SCIPOST_SUBSIDY_API_URL = (
    "https://scipost.org/api/subsidies/payments/?format=json"
)


def get_scipost_token() -> str:
    """
    Retrieve an authentication token from SciPost to access protected API.
    """
    print("Collecting OAuth2 token")
    auth_data = app_settings.SCIPOST_AUTH

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
            f"Token endpoint response: {token_data}"
        )
    print("Token obtained.")
    return token


def get_scipost_raw_data(
    api_url: str = SCIPOST_SUBSIDY_API_URL,
    dest_file: str = "",
) -> None:
    """
    Retrieve all scipost funding data from their API and dump it
    in the specified file.
    """
    print("Collecting Scipost funding data...")

    token = get_scipost_token()

    headers = {"Authorization": f"Bearer {token}"}

    data = requests.get(api_url, headers=headers).json()

    assert isinstance(data["results"], list), "ERROR - 'results' is not a list"

    results_data = {
        "total": data["count"],
        "total_received": len(data["results"]),
        "data_raw": data["results"],
    }

    query_url = data["next"]
    query_number = 1
    max_query = 100

    while query_url is not None:
        assert (
            query_number <= max_query
        ), "ERROR - Reached max number of queries."

        data = requests.get(query_url, headers=headers).json()
        query_number += 1

        assert isinstance(
            data["results"], list
        ), "ERROR - 'results' is not a list."
        assert (
            data["count"] == results_data["total"]
        ), "ERROR - Number of subsidies has change throughout collection."

        results_data["total_received"] += len(data["results"])
        results_data["data_raw"].extend(data["results"])

        query_url = data["next"]

    assert (
        results_data["total_received"] == results_data["total"]
    ), "ERROR - Total number of received subsidies =! from the API count."

    df = pd.DataFrame.from_records(results_data["data_raw"])

    print(
        f"Collected all SciPost funding data - {results_data["total"]} entries"
    )

    if dest_file:
        print(f"Dumping data to file: {dest_file}")

        with open(dest_file, "w") as f:
            df.to_json(
                f,
                orient="records",
                indent=2,
            )

        print("Dump done!")
    return df


def pre_process_data(df: pd.DataFrame):
    data = df.copy()
    data["hide_amount"] = ~data["amount_publicly_shown"]
    return data
