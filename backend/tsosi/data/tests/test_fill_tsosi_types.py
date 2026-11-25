import pytest
from django.core.management.base import CommandError

from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.management.commands.fill_tsosi_types import fill_types

from .factories import EntityFactory, IdentifierFactory


def entity_with_tsosi_id(value, **kwargs):
    entity = EntityFactory.create(**kwargs)
    IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_TSOSI, value=value
    )
    return entity


@pytest.mark.django_db
def test_fill_types(registries, tmp_path):
    rpo = entity_with_tsosi_id("T000001")
    consortium = entity_with_tsosi_id("T000002", tsosi_type="other")
    kept = entity_with_tsosi_id("T000003", tsosi_type="funder")
    untyped = entity_with_tsosi_id("T000004")
    path = tmp_path / "tsosi-entity-types.csv"
    path.write_text(
        "tsosi_id,tsosi_type,decided_by\n"
        "T000001,rpo,rule\n"
        "T000002,lib_consort,human\n"
        "T999999,company,rule\n"
    )

    fill_types(str(path))

    for entity in (rpo, consortium, kept, untyped):
        entity.refresh_from_db()
    assert rpo.tsosi_type == "rpo"
    assert consortium.tsosi_type == "lib_consort"
    # Not in the file: an existing type is kept, a missing one becomes other
    assert kept.tsosi_type == "funder"
    assert untyped.tsosi_type == "other"


@pytest.mark.django_db
def test_fill_types_unknown_type(registries, tmp_path):
    path = tmp_path / "tsosi-entity-types.csv"
    path.write_text(
        "tsosi_id,tsosi_type,decided_by\n"
        "T000001,library consortia,rule\n"
    )
    with pytest.raises(CommandError):
        fill_types(str(path))
