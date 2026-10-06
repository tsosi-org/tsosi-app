import logging
from dataclasses import dataclass, field

from tsosi.data import infra_lists
from tsosi.data.infra_lists import Infra
from tsosi.data.pid_registry.ror import (
    get_ror_country,
    get_ror_id,
    get_ror_inception_date,
    get_ror_name,
    get_ror_names,
    get_ror_website,
    get_ror_wikidata_id,
    get_ror_wikipedia_url,
)
from tsosi.data.utils import normalize_name

from . import sources
from .ticket import Ticket

logger = logging.getLogger(__name__)

BOT_MARKER = "<!-- tsosi-infra-curation-bot -->"
BOT_DOC_URL = "https://github.com/tsosi-org/tsosi-app/blob/main/backend/tsosi/data/infra_curation/README.md"
ROR_URL = "https://ror.org"
WIKIDATA_URL = "https://www.wikidata.org/wiki"

# Keys of the metadata table, in display order
FIELDS = [
    "Name",
    "Short name",
    "Description",
    "Country",
    "Creation Date",
    "Website",
    "Wikipedia URL",
    "ROR URL",
    "Wikidata URL",
    "How to support",
    "TSOSI URL",
    "TSOSI provider",
    "SCOSS",
    "POSI",
    "Barcelona Declaration",
    "Infrafinder",
]


@dataclass
class Curation:
    ticket: Ticket
    values: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def set(self, key: str, value):
        """
        Set the field value, unless it is empty or the field is already set:
        the calling order defines the priority of the sources.
        """
        if value is None or value == "" or self.values.get(key):
            return
        self.values[key] = str(value)

    def safe_call(self, description: str, func, *args):
        """
        Call `func`, reporting failures as warnings so that a source being
        down doesn't prevent the others from being used.
        """
        try:
            return func(*args)
        except Exception as e:
            logger.exception(f"Failed to {description}")
            self.warnings.append(f"Failed to {description}: `{e}`")
            return None


@dataclass
class Records:
    ror: dict | None = None
    wikidata: dict | None = None
    tsosi: dict | None = None


def fetch_ror(curation: Curation, records: Records, ror_id: str):
    records.ror = curation.safe_call(
        "fetch the ROR record", sources.fetch_ror_record, ror_id
    )


def fetch_wikidata(curation: Curation, records: Records, wikidata_id: str):
    result = curation.safe_call(
        "fetch the Wikidata record",
        sources.fetch_wikidata_records,
        [wikidata_id],
    )
    records.wikidata = (result or {}).get(wikidata_id)
    if result is not None and records.wikidata is None:
        curation.warnings.append(f"Wikidata item `{wikidata_id}` not found.")


def identify(curation: Curation) -> Records:
    """
    Fetch the records of the ROR, Wikidata or TSOSI ID given in the ticket,
    and complete them from each other's links.
    """
    ticket = curation.ticket
    records = Records()
    given_ids = [
        (label, value)
        for label, value in [
            ("TSOSI", ticket.tsosi_id),
            ("ROR", ticket.ror_id),
            ("Wikidata", ticket.wikidata_id),
        ]
        if value
    ]
    if not given_ids:
        curation.warnings.append(
            "No ROR, Wikidata or TSOSI ID found in the ticket: edit its "
            "identifier to fix it."
        )
        warn_tsosi_homonyms(curation)
        return records

    if ticket.tsosi_id:
        records.tsosi = curation.safe_call(
            "fetch the TSOSI entity",
            sources.fetch_tsosi_entity,
            ticket.tsosi_id,
        )
        if records.tsosi is None:
            curation.warnings.append(
                f"TSOSI entity `{ticket.tsosi_id}` not found."
            )
    ror_id = ticket.ror_id or tsosi_id(records.tsosi, "ror")
    if ror_id:
        fetch_ror(curation, records, ror_id)
    wikidata_id = (
        ticket.wikidata_id
        or tsosi_id(records.tsosi, "wikidata")
        or (records.ror and get_ror_wikidata_id(records.ror))
    )
    if wikidata_id:
        fetch_wikidata(curation, records, wikidata_id)

    ## Complete the ROR record from the Wikidata one
    ror_id = records.ror and get_ror_id(records.ror)
    wikidata_ror_id = (records.wikidata or {}).get("ror_id")
    if wikidata_ror_id and not records.ror:
        fetch_ror(curation, records, wikidata_ror_id)
    elif wikidata_ror_id and wikidata_ror_id != ror_id:
        curation.warnings.append(
            f"The Wikidata item links to the ROR ID `{wikidata_ror_id}` "
            f"instead of `{ror_id}`."
        )

    ## TSOSI entity, which can complete the ROR & Wikidata records
    for identifier in [
        records.ror and get_ror_id(records.ror),
        (records.wikidata or {}).get("id"),
    ]:
        if records.tsosi is None and identifier:
            records.tsosi = curation.safe_call(
                "fetch the TSOSI entity", sources.fetch_tsosi_entity, identifier
            )
    if records.tsosi:
        if records.ror is None and tsosi_id(records.tsosi, "ror"):
            fetch_ror(curation, records, tsosi_id(records.tsosi, "ror"))
        if records.wikidata is None and tsosi_id(records.tsosi, "wikidata"):
            fetch_wikidata(
                curation, records, tsosi_id(records.tsosi, "wikidata")
            )
    else:
        warn_tsosi_homonyms(curation)

    if records.ror is None and records.wikidata is None:
        curation.warnings.append(
            "No ROR or Wikidata record found for this infrastructure."
        )
    return records


def tsosi_id(entity: dict | None, registry: str) -> str | None:
    return sources.tsosi_identifier(entity, registry) if entity else None


def warn_tsosi_homonyms(curation: Curation):
    """
    Warn about the TSOSI entities with the ticket name. They are not used as
    an existing entity might be another organization with the same name.
    """
    name = normalize_name(curation.ticket.name)
    entities = curation.safe_call(
        "search TSOSI", sources.search_tsosi_entities, curation.ticket.name
    )
    for entity in entities or []:
        if name in (
            normalize_name(entity["name"]),
            normalize_name(entity.get("short_name")),
        ):
            curation.warnings.append(
                "A TSOSI entity has the same name: "
                f"[{entity["name"]}]({sources.tsosi_entity_url(entity)}). "
                "Edit the ticket to use its URL as identifier if it is the "
                "same organization."
            )


def fill_values(curation: Curation, records: Records):
    c = curation
    ror, tsosi = records.ror, records.tsosi
    wd = records.wikidata or {}
    infra_details = (tsosi or {}).get("infrastructure") or {}

    c.set("Name", ror and get_ror_name(ror))
    c.set("Name", wd.get("name"))
    c.set("Name", tsosi and tsosi["name"])
    c.set("Name", c.ticket.name)

    acronyms = [
        n["value"] for n in get_ror_names(ror or {}) if n["type"] == "acronym"
    ]
    c.set("Short name", tsosi and tsosi.get("short_name"))
    c.set("Short name", acronyms[0] if acronyms else None)

    c.set("Description", tsosi and tsosi.get("description"))

    c.set("Country", ror and get_ror_country(ror))
    c.set("Country", wd.get("country"))
    c.set("Country", tsosi and tsosi.get("country"))

    inception = ror and get_ror_inception_date(ror)
    c.set("Creation Date", (wd.get("date_inception") or "")[:10])
    c.set("Creation Date", inception and inception.year)
    c.set("Creation Date", tsosi and tsosi.get("date_inception"))

    c.set("Website", ror and get_ror_website(ror))
    c.set("Website", wd.get("website"))
    c.set("Website", tsosi and tsosi.get("website"))

    c.set("Wikipedia URL", ror and get_ror_wikipedia_url(ror))
    c.set("Wikipedia URL", wd.get("wikipedia_url"))
    c.set("Wikipedia URL", tsosi and tsosi.get("wikipedia_url"))

    c.set("ROR URL", ror and f"{ROR_URL}/{get_ror_id(ror)}")
    c.set("Wikidata URL", f"{WIKIDATA_URL}/{wd["id"]}" if wd else None)
    c.set("How to support", infra_details.get("support_url"))
    c.set("TSOSI URL", tsosi and sources.tsosi_entity_url(tsosi))
    c.set("TSOSI provider", str(bool(tsosi and tsosi["is_partner"])).lower())

    ## Lists of infrastructures
    names = [
        c.ticket.name,
        c.values.get("Name"),
        c.values.get("Short name"),
        wd.get("name"),
        *(n["value"] for n in get_ror_names(ror or {})),
    ]
    infra = Infra(
        names=[n for n in names if n],
        websites=[c.values["Website"]] if c.values.get("Website") else [],
        ror_id=get_ror_id(ror) if ror else None,
    )

    if tsosi and tsosi.get("is_scoss"):
        c.set("SCOSS", "true")
    scoss = c.safe_call("fetch the SCOSS Family", sources.scoss_family)
    match = infra_lists.find_entry(infra, scoss or [])
    if match:
        c.set("SCOSS", "true")
    if scoss is not None:
        c.set("SCOSS", "false")

    c.set("POSI", infra_details.get("posi_url"))
    posi = c.safe_call("fetch the POSI adopters", sources.posi_adopters)
    match = infra_lists.find_entry(infra, posi or [])
    if match:
        c.set("POSI", match.entry.url)

    if tsosi and tsosi.get("is_barcelona"):
        c.set("Barcelona Declaration", "true")
    barcelona = c.safe_call(
        "fetch the Barcelona Declaration", sources.barcelona_declaration
    )
    match = infra_lists.find_entry(infra, barcelona or [])
    if match:
        c.set("Barcelona Declaration", "true")
    if barcelona is not None:
        c.set("Barcelona Declaration", "false")

    c.set("Infrafinder", infra_details.get("infra_finder_url"))
    solutions = c.safe_call(
        "fetch the Infra Finder solutions", sources.infra_finder_solutions
    )
    match = c.safe_call(
        "look up Infra Finder",
        infra_lists.find_infra_finder_solution,
        infra,
        solutions or [],
    )
    if match:
        c.set("Infrafinder", match.entry.url)


def table_cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())


def render(curation: Curation) -> str:
    lines = [BOT_MARKER, "### Infrastructure metadata", ""]
    lines += ["| Key | Value |", "| -- | -- |"]
    lines += [
        f"| {key} | {table_cell(curation.values.get(key, ''))} |"
        for key in FIELDS
    ]
    if curation.warnings:
        lines += ["", "> [!WARNING]"]
        lines += [f"> - {w}" for w in curation.warnings]
    return "\n".join(lines) + "\n"


def curate(ticket: Ticket) -> str:
    """
    Return the metadata comment of the curation ticket.
    """
    curation = Curation(ticket)
    records = identify(curation)
    fill_values(curation, records)
    return render(curation)
