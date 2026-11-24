from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI, TSOSI_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX

from .registry import Registry
from .utils import MATCH_SOURCE_MANUAL  # noqa: F401 (re-exported)

REGISTRY_ROR = "ror"
REGISTRY_WIKIDATA = "wikidata"
REGISTRY_CUSTOM = "_custom"
CUSTOM_ID_REGEX = r"^.+$"

PID_REGISTRIES = [
    Registry(
        id=REGISTRY_ROR,
        name="Research Organization Registry",
        website="https://ror.org",
        link_template="https://ror.org/{id}",
        record_regex=ROR_ID_REGEX,
    ),
    Registry(
        id=REGISTRY_WIKIDATA,
        name="Wikidata",
        website="https://www.wikidata.org",
        link_template="https://www.wikidata.org/wiki/{id}",
        record_regex=WIKIDATA_ID_REGEX,
    ),
    Registry(
        id=REGISTRY_CUSTOM,
        name="Custom entity registry",
        website="",
        link_template="",
        record_regex=CUSTOM_ID_REGEX,
    ),
    Registry(
        id=REGISTRY_TSOSI,
        name="TSOSI entity registry",
        website="",
        link_template="",
        record_regex=TSOSI_ID_REGEX,
    ),
]

PID_REGEX_OPTIONS = [
    (REGISTRY_TSOSI, TSOSI_ID_REGEX),
    (REGISTRY_ROR, ROR_ID_REGEX),
    (REGISTRY_WIKIDATA, WIKIDATA_ID_REGEX),
    (REGISTRY_CUSTOM, CUSTOM_ID_REGEX),
]


def create_pid_registries():
    """
    Create the PID registries.
    """
    existing_registries = Registry.objects.all()
    ids = {r.id: r for r in existing_registries}
    for r in PID_REGISTRIES:
        registry = ids.get(r.id)
        if registry:
            r.save(force_update=True)
            continue
        r.save()


# The supports declared by the organizations in the Data Contribution Hub,
# published on approval of their submissions.
HUB_DATA_SOURCE = "tsosi_portal"


def fill_static_data():
    """
    Fill static data in the database: the PID registries.
    """
    create_pid_registries()
