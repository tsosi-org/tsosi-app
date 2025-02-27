from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from tsosi.app_settings import app_settings

from .entity import Entity
from .identifier import (
    MATCH_CRITERIA_FROM_INPUT,
    Identifier,
    IdentifierEntityMatching,
    Registry,
)
from .source import DataSource
from .utils import MATCH_SOURCE_MANUAL, replace_model_file

REGISTRY_ROR = "ror"
REGISTRY_WIKIDATA = "wikidata"
REGISTRY_CUSTOM = "_custom"
DOAB_OAPEN_ID = "doab_oapen"

PID_REGISTRIES = [
    Registry(
        id=REGISTRY_ROR,
        name="Research Organization Registry",
        website="https://ror.org",
        link_template="https://ror.org/{id}",
    ),
    Registry(
        id=REGISTRY_WIKIDATA,
        name="Wikidata",
        website="https://www.wikidata.org",
        link_template="https://www.wikidata.org/wiki/{id}",
    ),
    Registry(
        id=REGISTRY_CUSTOM,
        name="Custom entity registry",
        website="",
        link_template="",
    ),
]


def create_pid_registries():
    """
    Create the PID registries.
    """
    existing_registries = Registry.objects.all()
    ids = [r.id for r in existing_registries]
    for r in PID_REGISTRIES:
        if r.id in ids:
            continue
        r.save()


SUPPORTED_INFRASTRUCTURES = [
    {
        "id": "doaj",
        "pid": {"registry_id": REGISTRY_ROR, "value": "05amyt365"},
        "entity": {
            "raw_name": "Directory of Open Access Journals",
            "raw_website": "https://doaj.org",
            "name": "Directory of Open Access Journals",
            "website": "https://doaj.org",
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/doaj-directory-of-open-access-journals",
            "posi_url": "https://blog.doaj.org/2022/10/06/doaj-commits-to-the-principles-of-open-scholarly-infrastructure-posi",
            "is_scoss_awarded": True,
            "is_partner": True,
        },
    },
    {
        "id": "doab_oapen",
        "pid": {"registry_id": REGISTRY_CUSTOM, "value": DOAB_OAPEN_ID},
        "entity": {
            "raw_name": "OAPEN & Directory of Open Access Books",
            "raw_website": "https://www.doabooks.org",
            "name": "Directory of Open Access Books & OAPEN",
            "website": "https://www.doabooks.org",
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/directory-of-open-access-books",
            "posi_url": "https://oapen.hypotheses.org/524",
            "is_scoss_awarded": True,
            "is_partner": True,
            "description": """OAPEN supports the transition to open access for academic books by providing open infrastructure services to stakeholders, including the DOAB (Directory of Open Access Books), on which OAPEN works in partnership with Open Edition.""",
            "manual_logo": True,
        },
        "static_logo": "LOGO_oapen_doab.png",
    },
    {
        "id": "operas",
        "pid": {"registry_id": REGISTRY_ROR, "value": "00rfexj26"},
        "entity": {
            "raw_name": "OPERAS",
            "raw_website": "https://operas-eu.org",
            "name": "OPERAS",
            "website": "https://operas-eu.org",
            "infra_finder_url": None,
            "posi_url": "https://operas-eu.org/principles-of-open-scholarly-infrastructure-posi",
            "is_scoss_awarded": False,
            "is_partner": True,
        },
    },
    {
        "id": "pci",
        "pid": {"registry_id": REGISTRY_ROR, "value": "0315saa81"},
        "entity": {
            "raw_name": "Peer Community In",
            "raw_website": "https://peercommunityin.org",
            "name": "Peer Community In",
            "website": "https://peercommunityin.org",
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/peer-community-in",
            "posi_url": "https://peercommunityin.org/2024/04/11/posi/",
            "is_scoss_awarded": False,
            "is_partner": True,
        },
    },
    {
        "id": "scipost",
        "pid": {"registry_id": REGISTRY_WIKIDATA, "value": "Q52663237"},
        "entity": {
            "raw_name": "SciPost",
            "raw_website": "https://scipost.org",
            "name": "SciPost",
            "website": "https://scipost.org",
            "infra_finder_url": None,
            "posi_url": "https://scipost.org/posi",
            "is_scoss_awarded": True,
            "is_partner": True,
        },
    },
]


def update_infrastructures():
    """
    Create or update infrastructure data.
    """
    now = timezone.now()
    for infra in SUPPORTED_INFRASTRUCTURES:
        entity = Entity(**infra["entity"])
        create = False
        static_logo: str | None = infra.get("static_logo")
        try:
            identifier = Identifier.objects.get(**infra["pid"])
            entity = identifier.entity
        except ObjectDoesNotExist:
            identifier = Identifier(**infra["pid"])
            create = True
        # Create all instances if required:
        # Entity, Identifier, IdentifierEntityMacthing
        if create:
            entity.date_created = now
            entity.date_last_updated = now
            if static_logo:
                file_path = str(
                    app_settings.TSOSI_APP_DATA_DIR / "assets" / static_logo
                )
                replace_model_file(entity, "logo", file_path)
            entity.save()

            identifier.entity = entity
            identifier.date_created = now
            identifier.date_last_updated = now
            identifier.save()

            id_entity_matching = IdentifierEntityMatching()
            id_entity_matching.entity = entity
            id_entity_matching.identifier = identifier
            id_entity_matching.date_created = now
            id_entity_matching.date_last_updated = now
            id_entity_matching.match_source = MATCH_SOURCE_MANUAL
            id_entity_matching.match_criteria = MATCH_CRITERIA_FROM_INPUT
            id_entity_matching.save()

            continue

        # Otherwise, only update the entity with additional fields
        entity.save(update_fields=list(infra["entity"].keys()))
        if static_logo:
            if entity.logo.name == static_logo:
                continue
            file_path = app_settings.TSOSI_APP_DATA_DIR / "assets" / static_logo
            replace_model_file(entity, "logo", str(file_path))


# These are the same IDs as the supported infrastructures.
# We keep it separated because the project could grow with other data sources.
DATA_SOURCES = [
    "doaj_library",
    "doaj_publisher",
    "scipost",
    "pci",
    "doab_oapen_library",
    "doab_oapen_sponsor",
    "operas",
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
    Fill static data in the database.
    """
    create_pid_registries()
    update_infrastructures()
    create_sources()
