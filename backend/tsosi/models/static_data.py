import json
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.ror import ROR_ID_REGEX
from tsosi.data.pid_registry.wikidata import WIKIDATA_ID_REGEX
from tsosi.data.preparation.cleaning_utils import clean_cell_value

from .entity import Entity, InfrastructureDetails
from .identifier import (
    MATCH_CRITERIA_FROM_INPUT,
    Identifier,
    IdentifierEntityMatching,
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
]

PID_REGEX_OPTIONS = [
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


@transaction.atomic
def update_partners():
    """
    Create or update partners Entity data.
    WARNING: You need to manually change the pid associated to an
    infrastructure. Running this method will just create another entity
    with the new identifier.
    """
    now = timezone.now()
    file_path = (
        Path(__file__).resolve().parent.parent
        / "data/assets/supported_infrastructures.json"
    )
    with open(file_path, "r") as f:
        supported_infrastructures = json.load(f)
    for infra in supported_infrastructures:
        create = False
        static_logo: str | None = infra.get("static_logo")
        static_icon: str | None = infra.get("static_icon")
        # Normalize string values
        for k, v in infra["entity"].items():
            infra["entity"][k] = clean_cell_value(v)
        for k, v in infra["infrastructure"].items():
            infra["infrastructure"][k] = clean_cell_value(v)

        try:
            identifier = Identifier.objects.get(**infra["pid"])
            entity = identifier.entity
        except ObjectDoesNotExist:
            identifier = Identifier(**infra["pid"])
            entity = Entity(**infra["entity"])
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
            if static_icon:
                file_path = str(
                    app_settings.TSOSI_APP_DATA_DIR / "assets" / static_icon
                )
                replace_model_file(entity, "icon", file_path)
            entity.save()
            details = InfrastructureDetails(**infra["infrastructure"])
            details.entity = entity
            details.save()

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

        # Otherwise, only update the existing data with additional fields
        for field, value in infra["entity"].items():
            setattr(entity, field, value)
        entity.save(update_fields=list(infra["entity"].keys()))

        details: InfrastructureDetails = entity.infrastructure_details
        for field, value in infra["infrastructure"].items():
            setattr(details, field, value)
        details.save(update_fields=list(infra["infrastructure"].keys()))

        if static_logo:
            if entity.logo.name == static_logo:
                continue
            file_path = app_settings.TSOSI_APP_DATA_DIR / "assets" / static_logo
            replace_model_file(entity, "logo", str(file_path))
        if static_icon:
            file_path = str(
                app_settings.TSOSI_APP_DATA_DIR / "assets" / static_icon
            )
            replace_model_file(entity, "icon", file_path)


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
    "default",
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
    update_partners()
    create_sources()
