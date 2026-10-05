import asyncio
import time
from functools import cache

import requests

from tsosi.data import infra_lists
from tsosi.data.pid_registry.common import (
    TSOSI_USER_AGENT,
    perform_http_func_batch,
)
from tsosi.data.pid_registry.ror import get_ror_record
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.data.pid_registry.wikidata import fetch_wikidata_records_data

TSOSI_URL = "https://tsosi.org"
TSOSI_API_URL = f"{TSOSI_URL}/api"
TIMEOUT = 30
MAX_ATTEMPTS = 3


## ROR & Wikidata


def fetch_ror_record(ror_id: str) -> dict:
    results = asyncio.run(
        perform_http_func_batch([ror_id], get_ror_record, max_conns=1)
    )
    if results[0].error:
        raise RuntimeError(results[0].error_msg)
    return results[0].record


def fetch_wikidata_records(wikidata_ids: list[str]) -> dict[str, dict]:
    """
    Return the Wikidata records by ID, as processed by
    `pid_registry.wikidata.process_wikidata_results`.
    """
    if not wikidata_ids:
        return {}
    results = asyncio.run(fetch_wikidata_records_data(wikidata_ids))
    return {
        row["id"]: row["record"]
        for _, row in results.iterrows()
        if not row["error"]
    }


## TSOSI


def tsosi_get(path: str, **kwargs) -> requests.Response:
    """
    GET the TSOSI API path, waiting & retrying when the rate limit is hit.
    """
    for attempt in range(MAX_ATTEMPTS):
        response = requests.get(
            f"{TSOSI_API_URL}{path}",
            headers={"User-Agent": TSOSI_USER_AGENT},
            timeout=TIMEOUT,
            **kwargs,
        )
        if response.status_code != 429 or attempt == MAX_ATTEMPTS - 1:
            return response
        retry_after = response.headers.get("Retry-After", "")
        time.sleep(min(int(retry_after) if retry_after.isdigit() else 20, 60))


def fetch_tsosi_entity(identifier: str) -> dict | None:
    """
    Return the TSOSI entity with the given TSOSI, ROR or Wikidata ID.
    """
    response = tsosi_get(f"/entities/{identifier}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def search_tsosi_entities(name: str) -> list[dict]:
    response = tsosi_get("/entities", params={"search": name})
    response.raise_for_status()
    return response.json().get("results", [])


def tsosi_identifier(entity: dict, registry: str) -> str | None:
    return next(
        (
            i["value"]
            for i in entity.get("identifiers", [])
            if i["registry"] == registry
        ),
        None,
    )


def tsosi_entity_url(entity: dict) -> str:
    entity_ref = tsosi_identifier(entity, REGISTRY_TSOSI) or entity["id"]
    return f"{TSOSI_URL}/entities/{entity_ref}"


## Lists of infrastructures, fetched once per run

scoss_family = cache(infra_lists.fetch_scoss_family)
posi_adopters = cache(infra_lists.fetch_posi_adopters)
barcelona_declaration = cache(infra_lists.fetch_barcelona_declaration)
infra_finder_solutions = cache(infra_lists.fetch_infra_finder_solutions)
