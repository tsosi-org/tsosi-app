import pytest
from tsosi.data.enrichment.database_related import update_entity_active_status
from tsosi.models import Entity

from ..factories import EntityFactory, TransferFactory


@pytest.mark.django_db
def test_entity_active_status(datasources):
    print("Testing the Entity.is_active boolean update.")

    e_0 = EntityFactory.create()
    e_1 = EntityFactory.create()
    e_2 = EntityFactory.create(is_partner=True)

    update_entity_active_status()

    e_0.refresh_from_db()
    assert not e_0.is_active
    e_1.refresh_from_db()
    assert not e_1.is_active
    e_2.refresh_from_db()
    assert e_2.is_active

    t_1 = TransferFactory.create(emitter=e_1)
    update_entity_active_status()
    e_1.refresh_from_db()
    assert e_1.is_active

    t_1.delete()
    update_entity_active_status()
    e_1.refresh_from_db()
    assert not e_1.is_active

    t_1 = TransferFactory.create(recipient=e_1)
    update_entity_active_status()
    e_1.refresh_from_db()
    assert e_1.is_active

    t_1.delete()
    update_entity_active_status()
    e_1.refresh_from_db()
    assert not e_1.is_active

    t_1 = TransferFactory.create(agent=e_1)
    update_entity_active_status()
    e_1.refresh_from_db()
    assert e_1.is_active
