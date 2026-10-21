import pytest

from tsosi.data.enrichment.database_related import update_entities_relationships
from tsosi.models.static_data import REGISTRY_ROR

from ..factories import EntityFactory, IdentifierFactory


@pytest.mark.django_db
def test_entities_relationships(registries):
    child = EntityFactory.create()
    parent = EntityFactory.create()
    IdentifierFactory.create(
        entity=parent, registry_id=REGISTRY_ROR, value="02rx3b187"
    )
    history_count = child.history.count()

    update_entities_relationships({child.id: ["02rx3b187", "unknown"]})
    assert list(child.parents.all()) == [parent]

    update_entities_relationships({child.id: None})
    assert not child.parents.exists()
    # The parents are a many-to-many relation: the entity itself isn't saved,
    # so no empty history record is added.
    assert child.history.count() == history_count
