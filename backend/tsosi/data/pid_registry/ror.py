"""
Contains methods to fetch records from the ROR and to process it.
ROR API doc - https://ror.readme.io/docs/rest-api

WARNING:
"   No registration is required to use the ROR API,
    but note that the rate limit is a maximum of 2000 requests in
    a 5-minute period, and API traffic can be quite heavy
    at popular times like midnight UTC."
"""

import re
from dataclasses import asdict, dataclass, field
from json import JSONDecodeError
from typing import Iterable
from urllib.parse import urlencode

import aiohttp
import pandas as pd

from .common import ApiResult, HTTPStatusError, perform_http_func_batch

# doc: https://ror.readme.io/v2/docs/api-affiliation
ROR_API_ENDPOINT = "https://api.ror.org/v2/organizations"
ROR_ID_REGEX = r"[0-9a-zA-Z]{9}"
ES_RESERVED_CHARS = [
    "+",
    "-",
    "&",
    "|",
    "!",
    "(",
    ")",
    "{",
    "}",
    "[",
    "]",
    "^",
    '"',
    "~",
    "*",
    "?",
    ":",
    "\\",
    "/",
]


@dataclass(kw_only=True)
class RorRecordApiResult(ApiResult):
    """ """

    id: str
    record: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class RorAffiliationApiResult(ApiResult):
    """
    Dataclass to store the result of a ROR affiliation API request.
    """

    search_value: str
    matched_id: str | None = None
    matched_name: str | None = None
    matched_status: str | None = None
    matched_substring: str | None = None
    has_chosen_match: bool = False
    match_score: float | None = None
    match_type: str | None = None


async def match_ror_record(
    session: aiohttp.ClientSession, value: str
) -> RorAffiliationApiResult:
    """
    Query the ROR affiliation API with the given organization name.
    If no results is returned, try the ROR query API for inactive organizations.

    :param value:       The organization name to match
    :param session:     The aiohttp ClientSession object
    :return result:     The RorAffiliationApiResult
    """
    ror_result = RorAffiliationApiResult(search_value=value)
    search_term = value
    params = {"affiliation": search_term}
    request_url = f"{ROR_API_ENDPOINT}?{urlencode(params)}"
    try:
        async with session.get(request_url) as response:
            if response.status < 200 or response.status >= 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            query_response: dict = await response.json()
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        msg = "\n".join(
            [
                f"Error while querying ROR API for value {value} with url {request_url}:",
                str(e),
            ]
        )
        ror_result.error = True
        ror_result.error_message = msg
        return ror_result

    query_results = query_response.get("number_of_results", 0)

    if query_results > 0:
        item = query_response["items"][0]

        ror_result.matched_status = "active"
        ror_result.matched_id = item["organization"]["id"]
        ror_result.match_score = item["score"]
        ror_result.match_type = item["matching_type"]
        ror_result.matched_substring = item["substring"]

        names = item["organization"]["names"]
        for name in names:
            if "ror_display" in name["types"]:
                ror_result.matched_name = name["value"]
                break

        if item["chosen"] == True:
            ror_result.has_chosen_match = True

        return ror_result

    ## Try inactive records when no record was found within the active ones
    # We need to escape ES characters for the query API.
    for i in ES_RESERVED_CHARS:
        search_term = search_term.replace(i, "\\" + i)

    params = {"query": search_term, "filter": "status:inactive"}
    try:
        async with session.get(request_url) as response:
            if response.status < 200 or response.status >= 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            query_response: dict = await response.json()
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        msg = "\n".join(
            [
                f"Error while querying ROR API for value {value} with url {request_url}:",
                str(e),
            ]
        )
        ror_result.error = True
        ror_result.error_message = msg
        return ror_result

    query_results = query_response.get("number_of_results", 0)
    if query_results == 0:
        return ror_result

    ror_result.matched_status = "inactive"
    item = query_response["items"][0]
    ror_result.matched_id = item["id"]
    for name in item["names"]:
        if "ror_display" in name["types"]:
            ror_result.matched_name = name["value"]

    return ror_result


async def match_ror_records(names: Iterable[str]) -> pd.DataFrame:
    """
    Performs the single `match_ror_record` for every given value.
    This uses async http handling to speed up the process (12 times
    faster for ~1K http requests).

    :param data:          The iterable of organization names.
    :returns:       The dataframe of the results for each input name.
    """
    if len(names) == 0:
        print("Empty names passed to match ror records.")
        return pd.DataFrame()

    results = await perform_http_func_batch(names, match_ror_record)
    results = pd.DataFrame.from_records([asdict(r) for r in results])
    results["matched_id"] = results["matched_id"].apply(
        lambda url: (url[-9:] if not pd.isnull(url) else url)
    )

    columns = {col: f"ror_{col}" for col in results.columns}
    return results.rename(columns=columns)


async def get_ror_record(
    session: aiohttp.ClientSession, id: str
) -> RorRecordApiResult:
    """
    Fetch the ROR record of the given ID.
    """
    result = RorRecordApiResult(id=id)
    if not re.match(ROR_ID_REGEX, id):
        result.error_message = f"The provided ID is not a ROR ID: {id}"
        result.error = True
        return result

    url = f"{ROR_API_ENDPOINT}/{id}"
    try:
        async with session.get(url) as response:
            if response.status < 200 or response.status >= 300:
                raise HTTPStatusError(
                    f"Wrong HTTP status code: {response.status}"
                )
            result.record = await response.json()
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        result.error_message = "\n".join(
            [
                f"Error while querying ROR API with url {url}",
                f"Original exception:",
                str(e),
            ]
        )
        result.error = True
    return result


async def fetch_ror_records(identifiers: Iterable[str]):
    """
    Fetch records data from the ROR registry.
    """
    results = await perform_http_func_batch(identifiers, get_ror_record)
    return pd.DataFrame.from_records([asdict(r) for r in results])


def get_ror_id(record: dict) -> str | None:
    """
    Return the ROR ID from the ROR record.
    """
    id: str | None = record.get("id")
    if id is None:
        return None
    return id.split("/")[-1]


def get_ror_name(record: dict) -> str | None:
    """
    Return the official name from the ROR record.
    If no official name is found, it fallbacks in order of preference to:
    - English label
    - First label
    - First name entry
    """
    names: list = record.get("names", [])
    if len(names) == 0:
        return None
    name = next(
        (n["value"] for n in names if "ror_display" in n["types"]), None
    )
    if name is not None:
        return name
    # Fallback to the english name if no ror_display - This should not happen
    name = next(
        (
            n["value"]
            for n in names
            if n["lang"] == "en" and "label" in n["types"]
        ),
        None,
    )
    if name is not None:
        return name
    # Fallback to first label
    name = next(
        (n["value"] for n in names if "label" in n["types"]),
        None,
    )
    # Fallback to
    if name is not None:
        return name

    return names[0]["value"]


def get_ror_country(record: dict) -> str | None:
    """
    Return the country ISO alpha-2 code from the ROR record.
    """
    locations: list = record.get("locations", [])
    if len(locations) == 0:
        return None
    country_codes: list[str] = [
        l["geonames_details"]["country_code"] for l in locations
    ]
    country_codes = set(country_codes)
    if len(country_codes) > 1:
        print(
            "Found more than 1 country code in ROR registry "
            + f"for PID {record["id"]}: {country_codes}"
        )
    return country_codes.pop()


def get_ror_coordinates(record: dict) -> str | None:
    """
    Return the coordinates as a WKT POINT from the ROR record.
    """
    locations: list = record.get("locations", [])
    if len(locations) != 1:
        return None
    lat = locations[0]["geonames_details"]["lat"]
    lng = locations[0]["geonames_details"]["lng"]
    return f"POINT({lat} {lng})"


def get_ror_website(record: dict) -> str | None:
    """
    Return the website URL from the ROR record.
    """
    links = record.get("links", [])
    if len(links) == 0:
        return None
    return next((l["value"] for l in links if l["type"] == "website"), None)


def get_ror_wikipedia_url(record: dict) -> str | None:
    """
    Return the Wikipedia URL from the ROR record.
    """
    links = record.get("links", [])
    if len(links) == 0:
        return None
    return next((l["value"] for l in links if l["type"] == "wikipedia"), None)


def get_ror_wikidata_id(record: dict) -> str | None:
    """
    Return the Wikidata ID from the ROR record.
    TODO: The ROR record sometimes holds a single wikidata ID with a null
    "preferred" ? It's displayed normally on the ROR website.
    Ex: https://ror.org/00f7hpc57
    """
    ids = record.get("external_ids", [])
    if len(ids) == 0:
        return None
    wikidata_ids = next((i for i in ids if i["type"] == "wikidata"), None)
    if wikidata_ids is None:
        return None
    if len(wikidata_ids["all"]) == 1:
        return wikidata_ids["all"][0]
    return wikidata_ids["preferred"]


ROR_EXTRACT_MAPPING = {
    "id": get_ror_id,
    "name": get_ror_name,
    "country": get_ror_country,
    "website": get_ror_website,
    "wikipedia_url": get_ror_wikipedia_url,
    "wikidata_id": get_ror_wikidata_id,
    "coordinates": get_ror_coordinates,
}


def ror_record_extractor(
    record: dict, output_field_prefix: str = "ror"
) -> dict[str, str | None]:
    """
    Extract and return the interesting data from a ROR record.
    """
    return {
        f"{output_field_prefix}_{name}": func(record)
        for name, func in ROR_EXTRACT_MAPPING.items()
    }
