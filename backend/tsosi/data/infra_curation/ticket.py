import re
from dataclasses import dataclass, field

from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.tsosi import TSOSI_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX

TITLE_PREFIX = "[Infra curation]"
IDENTIFIER_FIELD = "Identifier"
# Value of the empty optional fields of issue forms
NO_RESPONSE = "_No response_"

ROR_URL_REGEX = r"ror\.org/(0[a-z0-9]{6}[0-9]{2})\b"
WIKIDATA_URL_REGEX = r"wikidata\.org/(?:wiki|entity)/(Q[0-9]+)\b"
TSOSI_URL_REGEX = r"tsosi\.org/(?:api/)?entities/(T[0-9]{6,})\b"


def is_curation_issue(title: str) -> bool:
    """
    Whether the issue title has the curation prefix, ignoring the case like
    the `startsWith` check of the GitHub workflow.
    """
    return title.strip().casefold().startswith(TITLE_PREFIX.casefold())


def parse_form(body: str) -> dict[str, str]:
    """
    Parse the fields of an issue created with an issue form: each field is
    a `### <label>` heading followed by its value.
    """
    fields = {}
    parts = re.split(r"^###[ \t]+(.+?)[ \t]*$", body, flags=re.MULTILINE)
    for label, value in zip(parts[1::2], parts[2::2]):
        value = value.strip()
        fields[label] = "" if value == NO_RESPONSE else value
    return fields


@dataclass
class Ticket:
    repo: str
    number: int
    title: str
    body: str
    fields: dict[str, str] = field(init=False)

    def __post_init__(self):
        self.body = self.body or ""
        self.fields = parse_form(self.body)

    @property
    def name(self) -> str:
        """
        The infrastructure name: the issue title without its `[...]` prefix.
        """
        return re.sub(r"^\s*\[[^\]]*\]\s*", "", self.title).strip()

    @property
    def identifier(self) -> str:
        return self.fields.get(IDENTIFIER_FIELD, "")

    def _find_id(self, url_regex: str, id_regex: str) -> str | None:
        """
        Return the ID given in the identifier field, as a bare ID or an URL.
        Issues created before the issue form have no identifier field: the
        ID can be anywhere in their body.
        """
        if re.match(id_regex, self.identifier):
            return self.identifier
        for text in (self.identifier, self.body):
            match = re.search(url_regex, text)
            if match:
                return match.group(1)
        return None

    @property
    def ror_id(self) -> str | None:
        return self._find_id(ROR_URL_REGEX, ROR_ID_REGEX)

    @property
    def wikidata_id(self) -> str | None:
        return self._find_id(WIKIDATA_URL_REGEX, WIKIDATA_ID_REGEX)

    @property
    def tsosi_id(self) -> str | None:
        return self._find_id(TSOSI_URL_REGEX, TSOSI_ID_REGEX)
