"""
Contains methods to fetch records from the ROR and to process it.
ROR API doc - https://ror.readme.io/docs/rest-api

WARNING:
"   No registration is required to use the ROR API,
    but note that the rate limit is a maximum of 2000 requests in
    a 5-minute period, and API traffic can be quite heavy
    at popular times like midnight UTC."
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from json import JSONDecodeError
from typing import Iterable
from urllib.parse import urlencode

import aiohttp
import pandas as pd

from .common import ApiResult, HTTPStatusError, perform_http_func_batch

logger = logging.getLogger(__name__)
logger_console = logging.getLogger("console_only")

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
class RorMatchingResult(ApiResult):
    """ """

    # Custom information
    search_value: str
    matched_status: str | None = None
    perfect_match: bool = False
    # Matching result from ROR API
    match_score: float | None = None
    match_type: str | None = None
    match_substring: str | None = None
    match_chosen: bool = False
    # Matched record info
    matched_id: str | None = None
    matched_name: str | None = None
    matched_country: str | None = None


@dataclass(kw_only=True)
class RorAffiliationApiResult(ApiResult):
    """
    Dataclass to store the result of a ROR affiliation API request.
    """

    search_value: str
    matched_status: str | None = None
    full_results: list = field(default_factory=list)


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
                f"Error while querying ROR affiliation API for value {value} with url {request_url}:",
                str(e),
            ]
        )
        ror_result.error = True
        ror_result.error_message = msg
        logger_console.warning(msg)
        return ror_result

    query_results = query_response.get("number_of_results", 0)

    if query_results > 0:
        ror_result.matched_status = "active"
        ror_result.full_results = query_response["items"]
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
                f"Error while querying ROR affiliation API for value {value} with url {request_url}:",
                str(e),
            ]
        )
        ror_result.error = True
        ror_result.error_message = msg
        logger_console.warning(msg)
        return ror_result

    query_results = query_response.get("number_of_results", 0)
    if query_results == 0:
        return ror_result

    ror_result.matched_status = "inactive"
    ror_result.full_results = query_response["items"]
    return ror_result


async def match_ror_records(
    names: Iterable[str], countries: Iterable[str | None] | None = None
) -> pd.DataFrame:
    """
    Performs the single `match_ror_record` for every given value.
    This uses async http handling to speed up the process (12 times
    faster for ~1K http requests).

    :param names:       The iterable of organization names.
    :param countries:   The iterable of organization's countries (optional).
                        It is used to determine a perfect match.
    :returns:           The dataframe of the results for each input name.
    """
    if len(names) == 0:
        logger_console.warning("Empty names passed to match ror records.")
        return pd.DataFrame()
    if len(countries) != len(names):
        raise ValueError(
            f"The length of the `names` and `countries` iterables don't match."
        )
    elif countries is None:
        countries = [None for _ in names]

    results = await perform_http_func_batch(names, match_ror_record)

    # Process results
    # TODO: Vectorize somehow ?
    processed_results = [
        process_ror_matching_result(result, country)
        for result, country in zip(results, countries)
    ]

    processed_results = pd.DataFrame.from_records(
        [asdict(r) for r in processed_results]
    )
    processed_results["matched_id"] = processed_results["matched_id"].apply(
        lambda url: (url[-9:] if not pd.isnull(url) else url)
    )

    columns = {col: f"ror_{col}" for col in processed_results.columns}
    return processed_results.rename(columns=columns)


def process_ror_matching_result(
    result: RorAffiliationApiResult, country: str | None = None
) -> RorMatchingResult:
    """
    Extract useful information from the result of the ROR affiliation API.
    The method extracts what we think is the best match for the input value and
    country.

    1 - Select the best match
        a - There are exact matches - take the one with same country as
            the provided one, else the first.
        b - There are None, take the first one
    2 - Extract the matching information & the match's base data
    (id, name, country)
    """
    processed_result = RorMatchingResult(
        search_value=result.search_value, matched_status=result.matched_status
    )
    if result.error or len(result.full_results) == 0:
        processed_result.error = result.error
        processed_result.error_message = result.error_message
        return processed_result

    matched_org = None
    # For active organizations API, the result contains the keys:
    # substring, score, matching_type, chosen & organization (the ROR record)
    if result.matched_status == "active":
        exact_matches = [
            res
            for res in result.full_results
            if res["matching_type"] == "EXACT" and res["score"] == 1
        ]
        if len(exact_matches) > 0:
            matching_result = exact_matches[0]
            if country is not None:
                for m in exact_matches:
                    matched_country = get_ror_country(m["organization"])
                    if matched_country == country:
                        matching_result = m
                        processed_result.perfect_match = True
                        break
        else:
            matching_result = result.full_results[0]

        processed_result.match_substring = matching_result["substring"]
        processed_result.match_score = matching_result["score"]
        processed_result.match_type = matching_result["matching_type"]
        processed_result.match_chosen = matching_result["chosen"]
        matched_org = matching_result["organization"]
    # If the result comes from the inactive API, there's no matching metrics
    # and the results are the matched records themselves
    elif result.matched_status == "inactive":
        matched_org = result.full_results[0]
    else:
        raise ValueError(
            f"Unsupported ROR matching status: {result.matched_status}"
        )

    processed_result.matched_id = matched_org["id"]
    processed_result.matched_name = get_ror_name(matched_org)
    processed_result.matched_country = get_ror_country(matched_org)
    return processed_result


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
        logger.warning(result.error_message)
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
        logger.warning(
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
