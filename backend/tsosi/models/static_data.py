from django.utils import timezone

from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI, TSOSI_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX

from .registry import Registry
from .source import DataSource
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


# These are the same IDs as the supported infrastructures.
# We keep it separated because the project could grow with other data sources.
DATA_SOURCES = [
    "basel",
    "couperin",
    "csal",
    "doab_oapen_library",
    "doab_oapen_sponsor",
    "doab_oapen",
    "doaj_library",
    "doaj_publisher",
    "doaj",
    "edch",
    "episciences",
    "gottingen",
    "inrae",
    "ird",
    "leuven",
    "liege",
    "mersenne",
    "mirabel",
    "olh",
    "operas",
    "opf",
    "pci",
    "pkp",
    "rennes",
    "reperes",
    "rotterdam",
    "scipost",
    "uga",
    "uminho",
    "unil",
    "urfist",
    "utrecht",
]


def create_sources():
    """ """
    now = timezone.now()
    existing_sources = DataSource.objects.all().values_list("id", flat=True)
    to_create = []
    for source_id in DATA_SOURCES:
        if source_id in existing_sources:
            continue
        source = DataSource()
        source.id = source_id
        source.date_created = now
        source.date_last_updated = now
        to_create.append(source)
    if len(to_create) == 0:
        return
    DataSource.objects.bulk_create(to_create)


def fill_static_data():
    """
    Fill static data in the database: PID registries and data sources.
    """
    create_pid_registries()
    create_sources()
