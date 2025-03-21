import pandas as pd
import requests
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


def filter_transfers(df: pd.DataFrame):
    mask = (df["status"].isin(["paid", "invoiced"])) & (
        ~df["payment_date"].isna() | ~df["invoice_date"].isna()
    )
    filtered = df[mask].reset_index(drop=True)
    return filtered


def pre_process_data(df: pd.DataFrame):
    data = filter_transfers(df)
    # Columns manipulation
    subsidies = pd.json_normalize(data["subsidy"]).add_prefix("subsidy_")
    data = pd.concat([data.drop(columns=["subsidy"]), subsidies], axis=1)
    data.rename(
        columns={
            "subsidy_organization.name": "emitter",
            "subsidy_organization.orgtype": "emitter_type",
            "subsidy_organization.country": "emitter_country",
            "subsidy_organization.ror_id": "emitter_ror_id",
            "subsidy_subsidy_type": "subsidy_type",
            "subsidy_amount_publicly_shown": "amount_publicly_shown",
        },
        inplace=True,
    )

    # Actual processing
    data["subsidy_url"] = "https://scipost.org" + data["subsidy_url"]
    data["hide_amount"] = ~data["amount_publicly_shown"]

    cols_of_interest = [
        "amount",
        "invoice_date",
        "payment_date",
        "emitter",
        "emitter_type",
        "emitter_country",
        "emitter_ror_id",
        "subsidy_description",
        "subsidy_url",
        "subsidy_type",
        "hide_amount",
        "subsidy_date_from",
        "subsidy_date_until",
    ]
    return data[cols_of_interest].copy()
