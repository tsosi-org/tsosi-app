"""
Look up a single organization identifier, ROR or Wikidata, to tell which
organization it is: e.g. when a member adds an organization missing from
TSOSI in the Data Contribution Hub.
"""

import asyncio
import re
from dataclasses import dataclass, field

from .common import perform_http_func_batch
from .ror import (
    ROR_ID_REGEX,
    get_ror_country,
    get_ror_name,
    get_ror_record,
    get_ror_website,
    get_ror_wikidata_id,
)
from .wikidata import (
    WIKIDATA_ID_REGEX,
    fetch_wikidata_sparql_query,
    process_wikidata_results,
)

# The IDs of the registries in the database (`Registry`)
REGISTRY_ROR = "ror"
REGISTRY_WIKIDATA = "wikidata"
REGISTRY_NAMES = {REGISTRY_ROR: "ROR", REGISTRY_WIKIDATA: "Wikidata"}

# The URLs that users are likely to paste instead of the ID
ROR_URL_REGEX = r"^(?:https?://)?(?:www\.)?ror\.org/"
WIKIDATA_URL_REGEX = (
    r"^(?:https?://)?(?:www\.|m\.)?wikidata\.org/(?:wiki|entity)/"
)


class RegistryError(Exception):
    """The registry couldn't be reached, or returned an error."""


@dataclass(kw_only=True)
class OrganizationRecord:
    registry: str
    id: str
    name: str | None
    country: str | None
    website: str | None
    # The organization's IDs in the other registries, from its record
    other_ids: dict[str, str] = field(default_factory=dict)
    # The full record
    record: dict = field(default_factory=dict)


def parse_organization_id(value: str) -> tuple[str, str] | None:
    """
    Return the registry and the ID of a ROR or Wikidata ID, or of its URL,
    or None if it's neither.
    """
    value = value.strip().rstrip("/")
    ror_id = re.sub(ROR_URL_REGEX, "", value, flags=re.IGNORECASE).lower()
    if re.match(ROR_ID_REGEX, ror_id):
        return REGISTRY_ROR, ror_id
    wikidata_id = re.sub(
        WIKIDATA_URL_REGEX, "", value, flags=re.IGNORECASE
    ).upper()
    if re.match(WIKIDATA_ID_REGEX, wikidata_id):
        return REGISTRY_WIKIDATA, wikidata_id
    return None


def fetch_organization_record(
    registry: str, value: str
) -> OrganizationRecord | None:
    """
    Fetch the record of the ROR or Wikidata ID. Return None if there is no
    record with this ID, and raise a `RegistryError` if the registry
    couldn't be reached.
    """
    if registry == REGISTRY_ROR:
        return fetch_ror_organization(value)
    if registry == REGISTRY_WIKIDATA:
        return fetch_wikidata_organization(value)
    raise ValueError(f"Unsupported registry: {registry}")


def fetch_ror_organization(ror_id: str) -> OrganizationRecord | None:
    result = asyncio.run(
        perform_http_func_batch([ror_id], get_ror_record, max_conns=1)
    )[0]
    if result.http_status == 404:
        return None
    if result.error:
        raise RegistryError(result.error_msg)
    record = result.record
    wikidata_id = get_ror_wikidata_id(record)
    return OrganizationRecord(
        registry=REGISTRY_ROR,
        id=ror_id,
        name=get_ror_name(record),
        country=get_ror_country(record),
        website=get_ror_website(record),
        other_ids={REGISTRY_WIKIDATA: wikidata_id} if wikidata_id else {},
        record=record,
    )


def fetch_wikidata_organization(wikidata_id: str) -> OrganizationRecord | None:
    result = asyncio.run(
        perform_http_func_batch(
            [[wikidata_id]], fetch_wikidata_sparql_query, max_conns=1
        )
    )[0]
    if result.error:
        raise RegistryError(result.error_msg)
    rows = process_wikidata_results(result)
    rows = rows[rows["id"] == wikidata_id]
    if rows.empty or rows.iloc[0]["error"]:
        return None
    record: dict = rows.iloc[0]["record"]
    # An unknown item has no label: its name would be its ID
    if not record or not record.get("name"):
        return None
    ror_id = record.get("ror_id")
    return OrganizationRecord(
        registry=REGISTRY_WIKIDATA,
        id=wikidata_id,
        name=record["name"],
        country=record.get("country"),
        website=record.get("website"),
        other_ids={REGISTRY_ROR: ror_id} if ror_id else {},
        record=record,
    )
