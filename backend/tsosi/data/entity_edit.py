"""
Manual edition of an entity's data by an external user granted with
a temporary `EntityEditAccess`.

Edited values that are computed from PID records (name, country, ...) are
stored in the entity's TSOSI identifier record, which has the highest
priority when computing those fields (see `update_entity_from_pid_records`).
This way, the manual edits are not overwritten by ROR/Wikidata refreshes.
"""

import logging
from datetime import date

import nh3
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI, generate_tsosi_id
from tsosi.data.signals import identifiers_created, identifiers_fetched
from tsosi.models import (
    Entity,
    EntityEditAccess,
    EntityEditLog,
    Identifier,
    IdentifierEntityMatching,
    InfrastructureDetails,
)
from tsosi.models.identifier import MATCH_CRITERIA_FROM_INPUT
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA
from tsosi.models.utils import MATCH_SOURCE_MANUAL

logger = logging.getLogger(__name__)

# Entity fields editable through an edit access.
ENTITY_FIELDS = [
    "name",
    "short_name",
    "country",
    "date_inception",
    "description",
    "is_barcelona",
    "website",
    "wikipedia_url",
]
INFRASTRUCTURE_FIELDS = [
    "support_url",
    "posi_url",
    "infra_finder_url",
    "date_scoss_start",
    "date_scoss_end",
]
EDITABLE_REGISTRIES = [REGISTRY_ROR, REGISTRY_WIKIDATA]

# Allowed HTML in entity descriptions, which are rendered as raw HTML.
DESCRIPTION_ALLOWED_TAGS = {"a", "b", "strong", "i", "em", "br", "p"}
DESCRIPTION_ALLOWED_ATTRIBUTES = {"a": {"href"}}


def sanitize_description(value: str | None) -> str | None:
    if value is None:
        return None
    value = nh3.clean(
        value,
        tags=DESCRIPTION_ALLOWED_TAGS,
        attributes=DESCRIPTION_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
    ).strip()
    return value or None


def json_value(value):
    """Format a python value for JSON storage."""
    if isinstance(value, date):
        return value.isoformat()
    return value


def update_tsosi_record(entity: Entity, values: dict) -> bool:
    """
    Update the entity's TSOSI identifier record with the given values.
    """
    identifier, created = Identifier.objects.get_or_create(
        registry_id=REGISTRY_TSOSI,
        entity=entity,
        defaults={"value": generate_tsosi_id()},
    )
    if created:
        IdentifierEntityMatching.objects.create(
            entity=entity,
            identifier=identifier,
            match_source=MATCH_SOURCE_MANUAL,
            match_criteria=MATCH_CRITERIA_FROM_INPUT,
            comments="Created from an entity edit.",
        )
    record = {}
    if identifier.current_version is not None:
        record = dict(identifier.current_version.value)
    for field, value in values.items():
        if value is None:
            record.pop(field, None)
        else:
            record[field] = json_value(value)
    _, new_version = identifier.get_or_create_version(record)
    return new_version


def update_identifiers(
    entity: Entity, identifiers: dict[str, str | None], grantee: str
) -> tuple[dict, list[str]]:
    """
    Add the given identifiers to the entity, for the registries where it has
    none.
    """
    changes = {}
    created_registries = []
    for registry_id, new_value in identifiers.items():
        if not new_value or entity.identifiers.filter(
            registry_id=registry_id
        ).exists():
            continue
        identifier = Identifier.objects.create(
            registry_id=registry_id, value=new_value, entity=entity
        )
        IdentifierEntityMatching.objects.create(
            entity=entity,
            identifier=identifier,
            match_source=MATCH_SOURCE_MANUAL,
            match_criteria=MATCH_CRITERIA_FROM_INPUT,
            comments=f"Entity edit by {grantee}.",
        )
        created_registries.append(registry_id)
        changes[f"identifiers.{registry_id}"] = {"old": None, "new": new_value}
    return changes, created_registries


@transaction.atomic
def apply_entity_edit(
    entity: Entity,
    access: EntityEditAccess,
    data: dict,
    logo: UploadedFile | None = None,
    icon: UploadedFile | None = None,
) -> dict:
    """
    Apply the given validated edit data to the entity.
    Only the keys present in `data` are updated.
    Return the performed changes, which are also logged.

    :param data:    The validated data. It can contain the keys from
                    `ENTITY_FIELDS`, plus:
                    - `identifiers`: {registry_id: value | None}
                    - `infrastructure`: {field: value} with fields from
                      `INFRASTRUCTURE_FIELDS`
    """
    changes = {}
    now = timezone.now()

    # Entity fields
    entity_values = {f: data[f] for f in ENTITY_FIELDS if f in data}
    if "description" in entity_values:
        entity_values["description"] = sanitize_description(
            entity_values["description"]
        )
    for field, value in entity_values.items():
        old_value = getattr(entity, field)
        if old_value != value:
            changes[field] = {
                "old": json_value(old_value),
                "new": json_value(value),
            }
            setattr(entity, field, value)
    if "wikipedia_url" in changes:
        # The extract of the new page will be fetched by the wiki data update
        entity.wikipedia_extract = None
        entity.date_wikipedia_fetched = None
    record_updated = False
    if changes:
        record_updated = update_tsosi_record(
            entity, {f: entity_values[f] for f in changes}
        )

    # Logo & icon. The previous files are kept in the storage, only
    # unlinked, so that they can be restored from the edit log.
    old_files = {}
    if logo is not None:
        old_files["logo"] = entity.logo.name or None
        entity.logo = logo
        entity.manual_logo = True
    if icon is not None:
        old_files["icon"] = entity.icon.name or None
        entity.icon = icon

    entity.save()
    for field, old_name in old_files.items():
        # The new file name is only known once saved
        changes[field] = {"old": old_name, "new": getattr(entity, field).name}

    # Infrastructure details
    infra_values = data.get("infrastructure")
    if infra_values:
        try:
            infra = entity.infrastructure_details
        except InfrastructureDetails.DoesNotExist:
            infra = InfrastructureDetails(entity=entity)
        infra_changed = False
        for field in INFRASTRUCTURE_FIELDS:
            if field not in infra_values:
                continue
            old_value = getattr(infra, field)
            new_value = infra_values[field]
            if old_value != new_value:
                changes[f"infrastructure.{field}"] = {
                    "old": json_value(old_value),
                    "new": json_value(new_value),
                }
                setattr(infra, field, new_value)
                infra_changed = True
        if infra_changed:
            infra.save()

    # Identifiers
    created_registries = []
    if data.get("identifiers"):
        id_changes, created_registries = update_identifiers(
            entity, data["identifiers"], access.grantee
        )
        changes.update(id_changes)

    access.date_last_used = now
    access.save(update_fields=["date_last_used", "date_last_updated"])
    if not changes:
        return changes

    EntityEditLog.objects.create(entity=entity, access=access, changes=changes)
    logger.info(
        f"Entity {entity.id} edited by {access.grantee}: "
        f"{list(changes.keys())}"
    )

    # Trigger the fetching of the new PID records and the re-computation of
    # the entity fields.
    if created_registries:
        identifiers_created.send(None, registries=created_registries)
    if record_updated or any(k.startswith("identifiers.") for k in changes):
        identifiers_fetched.send(None, registry_id=REGISTRY_TSOSI)
    return changes
