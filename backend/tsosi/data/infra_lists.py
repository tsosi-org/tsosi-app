import csv
import io
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests
from lxml import html as lxml_html

from tsosi.data.pid_registry.common import TSOSI_USER_AGENT
from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.utils import normalize_name, same_site

SCOSS_FAMILY_URL = "https://scoss.org/what-is-scoss/scossfamily/"
POSI_ADOPTERS_URL = "https://openscholarlyinfrastructure.org/adopters/"
BARCELONA_DECLARATION_CSV_URL = "https://barcelona-declaration.org/downloads/barcelonadeclaration_signatories_supporters.csv"
INFRA_FINDER_URL = "https://infrafinder.investinopen.org"
TIMEOUT = 30


def get_page(url: str) -> str:
    response = requests.get(
        url, headers={"User-Agent": TSOSI_USER_AGENT}, timeout=TIMEOUT
    )
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


@dataclass
class Infra:
    """
    What is known about an infrastructure to look it up in the lists.
    """

    names: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    ror_id: str | None = None

    def matches_name(self, name: str | None) -> bool:
        name = normalize_name(name)
        return bool(name) and name in {normalize_name(n) for n in self.names}


@dataclass
class ListEntry:
    """
    An organization of a list.
    """

    names: list[str]
    # URLs identifying the organization by their domain: website, blog post..
    urls: list[str] = field(default_factory=list)
    ror_id: str | None = None
    # URL to display for the entry, eg. the POSI statement
    url: str | None = None


# Matching criteria, from the strongest to the weakest
MATCH_CRITERIA = ["ROR ID", "website", "name"]


@dataclass
class Match:
    entry: ListEntry
    # One of `MATCH_CRITERIA`
    matched_on: str


def match_entry(infra: Infra, entry: ListEntry) -> str | None:
    """
    Return the criteria the list entry matches the infrastructure on, if any.
    """
    if entry.ror_id and entry.ror_id == infra.ror_id:
        return "ROR ID"
    if any(same_site(u, w) for u in entry.urls for w in infra.websites):
        return "website"
    if any(infra.matches_name(n) for n in entry.names):
        return "name"
    return None


def find_entry(infra: Infra, entries: list[ListEntry]) -> Match | None:
    """
    Return the entry best matching the infrastructure.
    """
    matches = [
        Match(entry, matched_on)
        for entry in entries
        if (matched_on := match_entry(infra, entry))
    ]
    if not matches:
        return None
    return min(matches, key=lambda m: MATCH_CRITERIA.index(m.matched_on))


def has_class(name: str) -> str:
    """
    XPath predicate matching the elements with the given class.
    """
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def text(element) -> str:
    """
    Return the text of the element, with normalized whitespaces.
    """
    return " ".join(element.text_content().split())


## SCOSS


def parse_scoss_family(html: str) -> list[ListEntry]:
    """
    The SCOSS Family infrastructures are the only external links of the page
    opened in a new tab without any styling class.
    """
    links = lxml_html.fromstring(html).xpath(
        '//a[@target="_blank" and @rel="noopener" and not(@class)]'
        '[not(contains(@href, "scoss.org"))]'
        '[not(contains(@href, "list-manage.com"))]'
    )
    return [
        ListEntry(
            names=[text(link)] if text(link) else [],
            urls=[link.get("href")],
            url=SCOSS_FAMILY_URL,
        )
        for link in links
    ]


def fetch_scoss_family() -> list[ListEntry]:
    return parse_scoss_family(get_page(SCOSS_FAMILY_URL))


## POSI


def parse_posi_adopters(html: str) -> list[ListEntry]:
    """
    The POSI adopters page is a table with the organization name in the
    first column and the links to its POSI statements in the yearly columns.
    The entry URL is the latest statement.
    """
    entries = []
    for row in lxml_html.fromstring(html).xpath("//table//tr[td]"):
        name = text(row.xpath("./td[1]")[0])
        urls = row.xpath("./td[position() > 1]//a/@href")
        if not name or not urls:
            continue
        # Adopters like "OAPEN and DOAB" group several infrastructures
        names = [name, *name.split(" and ")] if " and " in name else [name]
        entries.append(ListEntry(names=names, urls=urls, url=urls[-1]))
    return entries


def fetch_posi_adopters() -> list[ListEntry]:
    return parse_posi_adopters(get_page(POSI_ADOPTERS_URL))


## Barcelona Declaration


def parse_barcelona_declaration(content: str) -> list[ListEntry]:
    entries = []
    for row in csv.DictReader(io.StringIO(content)):
        ror_id = (row.get("ror") or "").replace("https://ror.org/", "")
        entries.append(
            ListEntry(
                names=[row["organization"]] if row.get("organization") else [],
                urls=[row["website"]] if row.get("website") else [],
                ror_id=ror_id if re.match(ROR_ID_REGEX, ror_id) else None,
            )
        )
    return entries


def fetch_barcelona_declaration() -> list[ListEntry]:
    return parse_barcelona_declaration(get_page(BARCELONA_DECLARATION_CSV_URL))


## Infra Finder


def parse_infra_finder_solutions(html: str) -> list[ListEntry]:
    """
    Parse the solution cards of the Infra Finder home page.
    The cards only have the solution name: its website & ROR ID are in the
    solution page, see `parse_infra_finder_solution`.
    """
    links = lxml_html.fromstring(html).xpath(
        f"//a[{has_class('m-solution-card__header-link')}]"
    )
    return [
        ListEntry(
            names=[text(link)],
            url=urljoin(INFRA_FINDER_URL, link.get("href")),
        )
        for link in links
    ]


def parse_infra_finder_solution(html: str, entry: ListEntry) -> ListEntry:
    """
    Complete the solution entry with the website (the large button of the
    page header) and the ROR ID of the solution page.
    """
    tree = lxml_html.fromstring(html)
    websites = tree.xpath(f"//a[{has_class('m-button--lg')}]/@href")
    ror_ids = [
        m.group(1)
        for href in tree.xpath('//a[contains(@href, "ror.org/")]/@href')
        if (m := re.match(r"https?://ror\.org/(\w+)", href))
    ]
    return ListEntry(
        names=entry.names,
        urls=websites[:1],
        ror_id=ror_ids[0] if ror_ids else None,
        url=entry.url,
    )


def fetch_infra_finder_solutions() -> list[ListEntry]:
    return parse_infra_finder_solutions(get_page(INFRA_FINDER_URL))


def find_infra_finder_solution(
    infra: Infra, solutions: list[ListEntry]
) -> Match | None:
    """
    Infra Finder has ~200 solutions and no API: only the pages of the
    solutions with a matching name are fetched to check their website and
    ROR ID.
    """
    for solution in solutions:
        if not any(infra.matches_name(n) for n in solution.names):
            continue
        html = get_page(solution.url)
        solution = parse_infra_finder_solution(html, solution)
        return Match(solution, match_entry(infra, solution) or "name")
    return None
