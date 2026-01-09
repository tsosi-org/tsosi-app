"""
Contains methods to fetch records from Wikimedia projects:
Wikidata, Wikipedia and Wikimedia Commons.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from itertools import chain as it_chain
from json import JSONDecodeError
from urllib.parse import quote, urlencode

import aiohttp
import pandas as pd
from tsosi.data.utils import chunk_sequence, clean_null_values

from .common import ApiResult, HTTPStatusError, perform_http_func_batch

logger = logging.getLogger(__name__)

WIKIDATA_ID_REGEX = r"^Q[0-9]+$"
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# https://en.wikipedia.org/api/rest_v1/#/Page%20content/get_page_summary__title_
WIKIPEDIA_SUMMARY_API_ENDPOINT = (
    "https://en.wikipedia.org/api/rest_v1/page/summary"
)

ALLOWED_IMG_FILE_FORMATS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".apng",
    ".ico",
]


@dataclass(kw_only=True)
class WikidataSparqlApiResult(ApiResult):
    identifiers: Sequence[str]
    records: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class WikipediaSummaryApiResult(ApiResult):
    title: str
    extract: str | None = None


@dataclass(kw_only=True)
class WikimediaFileApiResult(ApiResult):
    url: str
    file_bytes: bytes | None = None
    final_url: str | None = None


async def fetch_wikidata_sparql_query(
    session: aiohttp.ClientSession, identifiers: Sequence[str]
) -> list:
    """
    Query the Wikidata SPARQL query service with the given query.
    """
    result = WikidataSparqlApiResult(identifiers=identifiers)
    correct_ids = [id for id in identifiers if re.match(WIKIDATA_ID_REGEX, id)]
    if not correct_ids:
        result.error = True
        result.error_msg = "Malformed Wikidata Identifiers."
        return result

    ids_part = "\n\t\t".join([f"wd:{id}" for id in correct_ids])
    query = WIKIDATA_RECORD_QUERY_TEMPLATE.format(ids_part=ids_part)
    params = {"query": query, "format": "json"}
    result.info = query
    try:
        async with session.post(
            WIKIDATA_SPARQL_ENDPOINT, params=params
        ) as response:
            result.http_status = response.status
            if response.status < 200 or response.status > 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            content: dict = await response.json()
            result.records = content.get("results", {}).get("bindings", [])
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        # Log the error
        msg = (
            f"Failed to query the wikipedia sparql endpoint ({e}) with query:\n"
            f"{query}\n"
        )
        logger.warning(msg)
        result.error = True
        result.error_msg = msg

    result.timestamp = datetime.now(UTC)
    return result


WIKIDATA_RECORD_QUERY_TEMPLATE = """
SELECT
    ?item
    ?itemLabel
    ?itemDescription
    ?countryIsoCode
    ?logoUrl
    ?websiteUrl
    ?rorId
    ?wikipediaUrl
    ?coordinates
    ?inceptionDate
WHERE {{
    VALUES ?item {{ {ids_part} }}
    OPTIONAL {{ ?item wdt:P571 ?inceptionDate. }}
    OPTIONAL {{ ?item (wdt:P17/wdt:P297) ?countryIsoCode. }}
    OPTIONAL {{ ?item wdt:P154 ?logoUrl. }}
    OPTIONAL {{ ?item wdt:P856 ?websiteUrl. }}
    OPTIONAL {{ ?item wdt:P6782 ?rorId. }}
    OPTIONAL {{ ?item wdt:P625 ?coordinates. }}
    OPTIONAL {{
        ?wikipediaUrl rdf:type schema:Article;
        schema:about ?item;
        schema:inLanguage "en";
        schema:isPartOf <https://en.wikipedia.org/>.
    }}
    SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en".
    }}
}}
"""

WIKIDATA_EXTRACT_MAPPING = {
    "item": "id",
    "itemLabel": "name",
    "itemDescription": "description",
    "websiteUrl": "website",
    "countryIsoCode": "country",
    "logoUrl": "logo_url",
    "wikipediaUrl": "wikipedia_url",
    "rorId": "ror_id",
    "coordinates": "coordinates",
    "inceptionDate": "date_inception",
}


def process_wikidata_results(result: WikidataSparqlApiResult) -> pd.DataFrame:
    """ """
    if result.error:
        df = pd.DataFrame()
        df["id"] = result.identifiers
        df["error"] = result.error
        df["error_msg"] = result.error_msg
        df["record"] = None
        df["http_status"] = result.http_status
        df["timestamp"] = result.timestamp
        df["info"] = result.info
        clean_null_values(df)
        return df

    df = pd.DataFrame.from_records(result.records)
    df.rename(columns=WIKIDATA_EXTRACT_MAPPING, inplace=True)
    # Flatten the wikidata results
    for col in df.columns:
        df[col] = df[col].map(lambda x: x if pd.isnull(x) else x["value"])
    # Add missing columns
    for c in WIKIDATA_EXTRACT_MAPPING.values():
        if c not in df.columns:
            df[c] = None

    ## Result data cleaning
    # There might be duplicated rows per item when there are multiple values
    # for one of the queried relations.
    # Ideally, we need to take the best value for each relation when there's
    # a way to filter.
    bad_logo_url_mask = ~(
        df["logo_url"].str.startswith("http://commons.wikimedia.org")
        | df["logo_url"].str.startswith("https://commons.wikimedia.org")
    )
    df.loc[bad_logo_url_mask, "logo_url"] = None

    df["id"] = df["id"].apply(lambda x: x.split("/")[-1])

    bad_label_mask = df["name"] == df["id"]
    df.loc[bad_label_mask, "name"] = None

    df = df.groupby("id").first().reset_index()

    clean_null_values(df)
    df["record"] = df.apply(lambda row: row.to_dict(), axis=1)
    df = df[["id", "record"]].copy()

    df["error"] = result.error
    df["error_msg"] = result.error_msg
    df["http_status"] = result.http_status
    df["info"] = result.info

    # Add an empty row for missing records that were not returned by the API
    extra_ids = pd.DataFrame({"id": result.identifiers})
    to_append = extra_ids[~extra_ids["id"].isin(df["id"])].copy()
    if not to_append.empty:
        to_append["error"] = True
        to_append["error_msg"] = "Item not returned by Wikidata SPARQL query."
        df = pd.concat([df, to_append], axis=0)

    df["timestamp"] = result.timestamp
    clean_null_values(df)
    return df


async def fetch_wikidata_records_data(
    identifiers: Sequence[str],
) -> pd.DataFrame:
    """"""
    if len(identifiers) == 0:
        print("No identifiers to fetch wikidata records for.")
        return pd.DataFrame()

    identifier_chunks = [c for c in chunk_sequence(identifiers, 40)]

    results = await perform_http_func_batch(
        identifier_chunks, fetch_wikidata_sparql_query, max_conns=5
    )

    processed = pd.concat([process_wikidata_results(r) for r in results])
    return processed


async def fetch_wikipedia_page_extract(
    session: aiohttp.ClientSession, title: str
) -> WikipediaSummaryApiResult:
    """
    Query English Wikipedia REST API for the summary of the given page title.
    """
    result = WikipediaSummaryApiResult(title=title)
    query_params = {"redirect": True}
    url = f"{WIKIPEDIA_SUMMARY_API_ENDPOINT}/{title}?{urlencode(query_params)}"
    result.info = url
    try:
        async with session.get(url) as response:
            result.http_status = response.status
            if response.status < 200 or response.status > 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            summary: dict = await response.json()
            result.extract = summary.get("extract", None)

    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        result.error = True
        result.error_msg = f"Error while querying Wikipedia with url {url}"
        result.error_msg += f" Original exception: {e}"
        logger.warning(result.error_msg)

    result.timestamp = datetime.now(UTC)
    return result


async def fetch_wikipedia_page_extracts(titles: Sequence[str]) -> pd.DataFrame:
    """"""
    results = await perform_http_func_batch(
        titles, fetch_wikipedia_page_extract
    )
    return pd.DataFrame.from_records([asdict(r) for r in results])


async def fetch_wikimedia_file(
    session: aiohttp.ClientSession, url: str
) -> WikimediaFileApiResult:
    """
    Perform a single HTTP request for the given URL.
    The URL is expected to reference a Wikimedia file.
    """
    result = WikimediaFileApiResult(url=url)
    result.info = url
    headers = {"Referer": url}
    try:
        async with session.get(
            url, allow_redirects=True, headers=headers
        ) as response:
            result.http_status = response.status
            if response.status < 200 or response.status >= 300:
                raise HTTPStatusError(
                    f"Wrong HTTP status code {response.status}"
                )
            result.file_bytes = await response.read()
            result.final_url = str(response.url)
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        result.error = True
        result.error_msg = f"Error while querying {url}"
        result.error_msg += f"Original exception:\n{e}"
        logger.warning(result.error_msg)

    result.timestamp = datetime.now(UTC)
    return result


async def fetch_wikimedia_files(urls: Sequence[str]) -> pd.DataFrame:
    """
    Perform HTTP requests for every given URLs.
    The URLs are expected to be referencing a file in wikimedia.

    TODO: Rename and move this code and related methods/objects
    in a generic file fetching method.
    There's no special handling of the fact that it fecthes wikimedia files.
    It just performs HTTP GET on the provided URLs.
    """
    results = await perform_http_func_batch(urls, fetch_wikimedia_file, 1)
    return pd.DataFrame.from_records([asdict(r) for r in results])
