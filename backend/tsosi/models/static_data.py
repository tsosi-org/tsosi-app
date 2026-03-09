import json
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.tsosi import (
    REGISTRY_TSOSI,
    TSOSI_ID_REGEX,
    generate_tsosi_id,
)
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX
from tsosi.data.preparation.cleaning_utils import clean_cell_value

from .entity import Entity, InfrastructureDetails
from .identifier import (
    MATCH_CRITERIA_FROM_INPUT,
    Identifier,
    IdentifierEntityMatching,
    IdentifierVersion,
)
from .registry import Registry
from .source import DataSource
from .utils import MATCH_SOURCE_MANUAL, replace_model_file

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
    (REGISTRY_ROR, ROR_ID_REGEX),
    (REGISTRY_WIKIDATA, WIKIDATA_ID_REGEX),
    (REGISTRY_CUSTOM, CUSTOM_ID_REGEX),
    (REGISTRY_TSOSI, TSOSI_ID_REGEX),
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


@transaction.atomic
def update_static_entities() -> None:
    """
    Create or update Entity data from local static file. These will overwrite data from others registries.
    """
    now = timezone.now()
    file_path = (
        Path(__file__).resolve().parent.parent
        / "data/assets/static_entities.json"
    )
    with open(file_path, "r") as f:
        static_entities = json.load(f)
    for row in static_entities:
        for k, v in row.get("entity", {}).items():
            row["entity"][k] = clean_cell_value(v)
        for k, v in row.get("infrastructure", {}).items():
            row["infrastructure"][k] = clean_cell_value(v)

        identifier, _ = Identifier.objects.get_or_create(
            **row["pid"],
            defaults={
                "date_created": now,
                "date_last_updated": now,
            },
        )
        if identifier.entity_id is None:
            # Create entity
            entity = Entity.objects.create(
                **row["entity"],
                date_created=now,
                date_last_updated=now,
            )
            identifier.entity = entity
            identifier.save()
            id_entity_matching = IdentifierEntityMatching(
                entity=entity,
                identifier=identifier,
                date_created=now,
                date_last_updated=now,
                match_source=MATCH_SOURCE_MANUAL,
                match_criteria=MATCH_CRITERIA_FROM_INPUT,
            )
            id_entity_matching.save()
        else:
            # Update entity
            entity = identifier.entity
            static_logo: str | None = row.get("static_logo")
            if static_logo:
                entity.logo = File(
                    open(
                        str(
                            app_settings.TSOSI_APP_DATA_DIR
                            / "assets"
                            / static_logo
                        ),
                        "rb",
                    )
                )
                entity.manual_logo = True
            else:
                entity.manual_logo = False
            static_icon: str | None = row.get("static_icon")
            if static_icon:
                entity.icon = File(
                    open(
                        str(
                            app_settings.TSOSI_APP_DATA_DIR
                            / "assets"
                            / static_icon
                        ),
                        "rb",
                    ),
                    name=static_icon,
                )
            else:
                entity.icon = None
            entity.save()

        if row.get("infrastructure"):
            InfrastructureDetails.objects.update_or_create(
                entity=entity,
                defaults={**row["infrastructure"], "entity": entity},
            )
        ## Create tsosi version if needed
        if row.get("entity"):
            tsosi_identifier, _ = Identifier.objects.get_or_create(
                registry_id=REGISTRY_TSOSI,
                entity=entity,
                defaults={"value": generate_tsosi_id()},
            )
            row["entity"].pop("logo", None)
            row["entity"].pop("icon", None)
            tsosi_identifier.get_or_create_version(row["entity"])


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
    "uga",
    "uminho",
    "couperin",
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
    update_static_entities()
    create_sources()
