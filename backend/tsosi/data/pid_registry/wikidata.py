"""
Contains methods to fetch records from Wikimedia projects:
Wikidata, Wikipedia and Wikimedia Commons.

#### API Rate limits ####

WIKIDATA SPARQL:
https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits
---
    - One client (user agent + IP) is allowed 60 seconds of processing time
    each 60 seconds
    - One client is allowed 30 error queries per minute
---

WIKIPEDIA REST API:
https://en.wikipedia.org/api/rest_v1/
---
Limit your clients to no more than 200 requests/s to this API. Each
API endpoint's documentation may detail more specific usage limits.
---


WIKIMEDIA COMMONS:

"""

import logging
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from itertools import chain as it_chain
from json import JSONDecodeError
from urllib.parse import quote, urlencode

import aiohttp
import pandas as pd
from tsosi.data.utils import chunk_sequence, clean_null_values

from .common import (
    ApiRateLimit,
    ApiResult,
    HTTPStatusError,
    perform_http_func_batch,
)

logger = logging.getLogger(__name__)

WIKIDATA_ID_REGEX = r"Q[0-9]+"
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# https://en.wikipedia.org/api/rest_v1/#/Page%20content/get_page_summary__title_
WIKIPEDIA_SUMMARY_API_ENDPOINT = (
    "https://en.wikipedia.org/api/rest_v1/page/summary"
)
WIKIMEDIA_RATE_LIMIT = ApiRateLimit(max_requests=100, time=1)

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
class WikidataRecordApiResult(ApiResult):
    id: str
    record: dict = field(default_factory=dict)


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
    session: aiohttp.ClientSession, query: str
) -> list:
    """
    Query the Wikidata SPARQL query service with the given query.
    """
    params = {"query": query, "format": "json"}
    try:
        async with session.post(
            WIKIDATA_SPARQL_ENDPOINT, params=params
        ) as response:
            if response.status < 200 or response.status > 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            results: dict = await response.json()
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        # Log the error
        logger.warning(
            f"Failed to query the wikipedia sparql endpoint with query:\n {query}"
        )
        return []
    return results.get("results", {}).get("bindings", [])


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
WHERE {{
    VALUES ?item {{ {ids_part} }}
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
        bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".
    }}
}}
"""


def format_wikidata_record_query(identifiers: Sequence[str]) -> str:
    """"""
    ids_part = "\n\t\t".join([f"wd:{id}" for id in identifiers])
    return WIKIDATA_RECORD_QUERY_TEMPLATE.format(ids_part=ids_part)


async def fetch_wikidata_records_data(
    identifiers: Sequence[str],
) -> pd.DataFrame:
    """"""
    if len(identifiers) == 0:
        print("No identifiers to fetch wikidata records for.")
        return pd.DataFrame()

    queries: list[str] = []
    for chunk in chunk_sequence(identifiers, 40):
        queries.append(format_wikidata_record_query(chunk))

    results = await perform_http_func_batch(
        queries, fetch_wikidata_sparql_query, max_conns=10
    )
    results = list(it_chain.from_iterable(results))
    if len(results) == 0:
        return pd.DataFrame()

    df = pd.DataFrame.from_records(results)
    # Flatten the results
    for col in df.columns:
        df[col] = df[col].map(lambda x: x if pd.isnull(x) else x["value"])
    df.drop_duplicates(subset="item", inplace=True)
    df["item"] = df["item"].apply(lambda x: x.split("/")[-1])
    col_mapping = {
        "item": "id",
        "itemLabel": "name",
        "itemDescription": "description",
        "websiteUrl": "website",
        "countryIsoCode": "country",
        "logoUrl": "logo_url",
        "wikipediaUrl": "wikipedia_url",
        "rorId": "ror_id",
        "coordinates": "coordinates",
    }
    df.rename(columns=col_mapping, inplace=True)
    # Add missing columns
    for c in col_mapping.values():
        if c not in df.columns:
            df[c] = None

    clean_null_values(df)
    df["record"] = df.apply(lambda row: row.to_dict(), axis=1)
    # Add no error for compatibility
    df["error"] = False

    return df[["id", "record"]].copy()


def format_wikipedia_page_title(title: str) -> str:
    """
    Format the given title to wikipedia title format:
        -   Replace spaces with underscores "_"
        -   %-encode the string
    """
    formatted_title = re.sub(r"\s+", "_", title)
    return quote(formatted_title, safe="")


async def fetch_wikipedia_page_extract(
    session: aiohttp.ClientSession, title: str
) -> WikipediaSummaryApiResult:
    """
    Query English Wikipedia REST API for the summary of the given page title.
    """
    result = WikipediaSummaryApiResult(title=title)
    query_params = {"redirect": True}
    url = f"{WIKIPEDIA_SUMMARY_API_ENDPOINT}/{title}?{urlencode(query_params)}"
    try:
        async with session.get(url) as response:
            if response.status < 200 or response.status > 300:
                raise HTTPStatusError(f"Wrong status code: {response.status}")
            summary: dict = await response.json()
            result.extract = summary.get("extract", None)

    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        result.error = True
        result.error_message = f"Error while querying Wikipedia with url {url}"
        result.error_message += f"\nOriginal exception:\n{e}"
        logger.warning(result.error_message)

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
    try:
        async with session.get(url, allow_redirects=True) as resp:
            if resp.status < 200 or resp.status >= 300:
                raise HTTPStatusError(f"Wrong HTTP status code {resp.status}")
            result.file_bytes = await resp.read()
            result.final_url = str(resp.url)
    except (HTTPStatusError, aiohttp.ClientError, JSONDecodeError) as e:
        result.error = True
        result.error_message = f"Error while querying {url}"
        result.error_message += f"Original exception:\n{e}"
        logger.warning(result.error_message)

    return result


async def fetch_wikimedia_files(urls: Sequence[str]) -> pd.DataFrame:
    """
    Perform HTTP requests for every given URLs.
    The URLs are expected to be referencing a file in wikimedia.
    """
    results = await perform_http_func_batch(urls, fetch_wikimedia_file)
    return pd.DataFrame.from_records([asdict(r) for r in results])
