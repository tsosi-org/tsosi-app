import json
import re
from datetime import date

import pandas as pd
import requests

ROR_REGEX = re.compile(r"https://ror\.org/([0-9a-zA-Z]{9})")
SCIPOST_SUBSIDY_API_URL = "https://scipost.org/api/subsidies/?format=json"
SCIPOST_ORGANIZATION_URL = "https://scipost.org/organizations/"


def get_scipost_raw_data(
    api_url: str = SCIPOST_SUBSIDY_API_URL,
    dest_file: str = "",
) -> None:
    """
    Retrieve all scipost funding data from their API and dump it
    in the specified file.
    """
    print("Collecting Scipost funding data...")

    data = requests.get(api_url).json()

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

        data = requests.get(query_url).json()
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

    df = pd.DataFrame(results_data["data_raw"])
    df["currency"] = "EUR"
    df = df.join(
        pd.json_normalize(df["organization"]).add_prefix("organization_")
    )
    df.drop("organization", axis=1, inplace=True)

    print(
        f"Collected all SciPost funding data - {results_data["total"]} entries"
    )

    if not dest_file:
        dest_file = f"{date.today().strftime("%Y-%m-%d")}_scipost_raw_data.json"
    print(f"Dumping data to file: {dest_file}")

    with open(dest_file, "w") as f:
        df.to_json(
            f,
            orient="records",
            indent=2,
        )

    print("Dump done!")


def find_ror_from_scipost(org_id: int) -> str | None:
    """
    Find the ROR ID of a scipost organization by scrapping its web page.

    :param org_id:  The scipost organization ID.
    :reutrns:       The ROR ID.
    """

    try:
        resp = requests.get(f"{SCIPOST_ORGANIZATION_URL}{org_id}/", timeout=4)
        html_string = resp.content.decode()
        res = ROR_REGEX.findall(html_string)
        if len(res) == 0:
            raise Exception("No ROR ID found.")

        ror_id = res[0]
        assert all(id == ror_id for id in res), f"Error - Mismatching ids {res}"
    except Exception as e:
        print(f"Error for organization ID {org_id} : {e}")
        return None

    print(f"Organisation {org_id} has ROR ID: {ror_id}")
    return ror_id


def enrich_scipost_raw_data(source_file: str, dest_file: str = "") -> None:
    """Read scipost raw data and scrap the ROR ID of every organization"""
    organization_ror = {}
    with open(source_file, "r") as f:
        data = json.loads(f.read())

    for d in data:
        match = re.match(
            rf"{SCIPOST_ORGANIZATION_URL}(\d+).+", d["organization_url"]
        )
        if not match:
            continue

        org_id = match[1]
        if org_id in organization_ror:
            d["organization_ror_id"] = organization_ror[org_id]
            continue
        ror_id = find_ror_from_scipost(org_id)
        d["organization_ror_id"] = ror_id
        organization_ror[org_id] = ror_id

    if not dest_file:
        dest_file = f"{date.today().strftime("%Y-%m-%d")}_scipost_data_with_scrapped_ror.json"

    print(f"Dumping data to file: {dest_file}")
    with open(dest_file, "w") as f:
        json.dump(
            data,
            f,
            indent=2,
        )
