from tsosi.data.infra_curation import sources
from tsosi.data.infra_curation.curation import (
    Curation,
    identify,
    render,
)
from tsosi.data.infra_curation.ticket import (
    Ticket,
    is_curation_issue,
    parse_form,
)
from tsosi.data.infra_lists import (
    Infra,
    ListEntry,
    find_entry,
    parse_barcelona_declaration,
    parse_infra_finder_solution,
    parse_infra_finder_solutions,
    parse_posi_adopters,
    parse_scoss_family,
)
from tsosi.data.utils import normalize_name, same_site

FORM_BODY = """### Asked by

Erasmus University Rotterdam

### Identifier

{}
"""

LEGACY_BODY = (
    "**Asked by** : Erasmus University Rotterdam\n\n   Key |  Value\n-- | --\n"
    "Name | CrimRxiv\nShort name | \xa0\nWebsite | https://www.crimrxiv.com/\n"
    "Wikipedia URL | \xa0\nROR URL | \xa0\n"
    "Wikidata URL | https://www.wikidata.org/wiki/Q123\n"
)


def form_ticket(identifier: str, title="[Infra curation] DOAJ") -> Ticket:
    return Ticket("org/repo", 1, title, FORM_BODY.format(identifier))


def test_is_curation_issue():
    assert is_curation_issue("[Infra curation] CrimRxiv")
    assert is_curation_issue(" [infra Curation] CrimRxiv")
    assert not is_curation_issue("CrimRxiv: Integrate data")


def test_parse_form():
    body = FORM_BODY.format("_No response_")
    assert parse_form(body) == {
        "Asked by": "Erasmus University Rotterdam",
        "Identifier": "",
    }


def test_ticket_identifiers():
    ticket = form_ticket("https://ror.org/05amyt365")
    assert ticket.name == "DOAJ"
    assert (ticket.ror_id, ticket.wikidata_id, ticket.tsosi_id) == (
        "05amyt365",
        None,
        None,
    )

    assert form_ticket("05amyt365").ror_id == "05amyt365"
    assert form_ticket("Q1227538").wikidata_id == "Q1227538"
    url = "https://www.wikidata.org/wiki/Q1227538"
    assert form_ticket(url).wikidata_id == "Q1227538"
    assert form_ticket("https://tsosi.org/entities/T978770").tsosi_id == (
        "T978770"
    )
    ticket = form_ticket("https://doaj.org")
    assert (ticket.ror_id, ticket.wikidata_id, ticket.tsosi_id) == (
        None,
        None,
        None,
    )


def test_legacy_ticket():
    ticket = Ticket("org/repo", 1, "[Infra curation] CrimRxiv", LEGACY_BODY)
    assert ticket.name == "CrimRxiv"
    assert ticket.ror_id is None
    assert ticket.wikidata_id == "Q123"


def test_normalize_name():
    assert normalize_name("Wikimédia  France") == "wikimedia france"
    assert normalize_name("ROR (CDL, Crossref, DataCite)") == "ror"
    assert normalize_name("HAL+ (CNRS)") == "hal+"
    assert normalize_name(None) == ""


def test_same_site():
    assert same_site("http://www.doaj.org/", "https://doaj.org")
    assert same_site("https://blog.core.ac.uk/2022/posi", "core.ac.uk")
    assert not same_site("https://sfu.ca", "https://pkp.sfu.ca")
    assert not same_site("https://github.com/b", "https://github.com/a")
    assert not same_site(None, "https://doaj.org")


def test_parse_scoss_family():
    html = """
    <a href="https://scoss.org/faq/" target="_blank" rel="noopener">FAQ</a>
    <a href="https://doaj.org/" target="_blank" rel="noopener">DOAJ</a>
    <a href="https://www.episciences.org/" target="_blank" rel="noopener"><img></a>
    <a href="https://twitter.com/scoss" rel="noopener noreferrer" target="_blank" class="no-icon">X</a>
    """
    entries = parse_scoss_family(html)
    assert [(e.names, e.urls) for e in entries] == [
        (["DOAJ"], ["https://doaj.org/"]),
        ([], ["https://www.episciences.org/"]),
    ]


def test_parse_posi_adopters():
    html = """<table>
    <thead><tr><th>Organization</th><th>2024</th><th>2025</th></tr></thead>
    <tbody>
    <tr><td>OAPEN and DOAB</td><td><a href="https://a.org/1">2023</a></td>
        <td><a href="https://a.org/2">2025</a></td></tr>
    <tr><td>Empty</td><td></td><td></td></tr>
    </tbody></table>"""
    entries = parse_posi_adopters(html)
    assert len(entries) == 1
    assert entries[0].names == ["OAPEN and DOAB", "OAPEN", "DOAB"]
    assert entries[0].url == "https://a.org/2"


def test_parse_barcelona_declaration():
    content = (
        "display_name,organization,website,ror\n"
        "DOAJ,DOAJ,https://doaj.org,https://ror.org/05amyt365\n"
        "Other,Other,,\n"
    )
    entries = parse_barcelona_declaration(content)
    assert entries[0].ror_id == "05amyt365"
    assert entries[1] == ListEntry(names=["Other"], urls=[], ror_id=None)


def test_parse_infra_finder():
    home = """<h3><a data-turbo-frame="_top" class="m-solution-card__header-link"
        href="/solutions/pombase">PomBase</a></h3>"""
    solutions = parse_infra_finder_solutions(home)
    assert solutions[0].names == ["PomBase"]
    assert solutions[0].url == (
        "https://infrafinder.investinopen.org/solutions/pombase"
    )
    page = """
    <a href="https://www.pombase.org/" class="m-button m-button--lg">Site</a>
    <a href="https://ror.org/013meh722" class="m-button m-button--sm">ROR</a>
    """
    solution = parse_infra_finder_solution(page, solutions[0])
    assert solution.urls == ["https://www.pombase.org/"]
    assert solution.ror_id == "013meh722"


def test_find_entry_prefers_strongest_match():
    infra = Infra(
        names=["DOAJ"], websites=["https://doaj.org"], ror_id="05amyt365"
    )
    entries = [
        ListEntry(names=["DOAJ"], url="by-name"),
        ListEntry(names=["X"], urls=["https://doaj.org/about"], url="by-site"),
        ListEntry(names=["Y"], ror_id="05amyt365", url="by-ror"),
    ]
    assert find_entry(infra, entries).entry.url == "by-ror"
    assert find_entry(infra, entries[:2]).entry.url == "by-site"
    assert find_entry(infra, entries[:1]).matched_on == "name"
    assert find_entry(Infra(names=["Other"]), entries) is None


def test_identify_without_id(monkeypatch):
    homonym = {"id": "x", "name": "DOAJ", "identifiers": []}
    monkeypatch.setattr(sources, "search_tsosi_entities", lambda _: [homonym])
    curation = Curation(form_ticket("https://doaj.org"))
    records = identify(curation)
    assert (records.ror, records.wikidata, records.tsosi) == (None, None, None)
    assert len(curation.warnings) == 2
    assert "No ROR, Wikidata or TSOSI ID" in curation.warnings[0]
    assert "https://tsosi.org/entities/x" in curation.warnings[1]


def test_render():
    curation = Curation(form_ticket("https://doaj.org"))
    curation.set("Name", "A | B")
    curation.set("Name", "Ignored")
    comment = render(curation)
    assert comment.startswith("<!-- tsosi-infra-curation-bot -->")
    assert "| Name | A \\| B |" in comment
    assert "| Infrafinder |  |" in comment
