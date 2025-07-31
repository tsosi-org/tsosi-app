import pandas as pd
import pytest
from django.core.exceptions import ObjectDoesNotExist
from tsosi.data.enrichment import new_identifiers_from_records
from tsosi.models import Entity, Identifier
from tsosi.models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

from ..factories import EntityFactory, IdentifierFactory


@pytest.mark.django_db
def test_new_wikidata_identifier_from_record(registries, mocker):
    print("Testing new wikidata identifier creation from record.")
    e = EntityFactory.create()
    i_ror = IdentifierFactory.create(registry_id=REGISTRY_ROR, entity=e)
    new_wikidata_id = "Q12345"
    with pytest.raises(ObjectDoesNotExist):
        Identifier.objects.get(value=new_wikidata_id)

    mock_data = pd.DataFrame(
        [
            {
                "id": e.id,
                "name": e.name,
                "ror_id": i_ror.value,
                "ror_wikidata_id": new_wikidata_id,
                "wikidata_id": None,
                "wikidata_ror_id": None,
            }
        ]
    )
    mocker.patch(
        "tsosi.data.enrichment.database_related.entities_with_identifier_data",
        return_value=mock_data,
    )

    new_identifiers_from_records(REGISTRY_WIKIDATA)
    new_id = Identifier.objects.get(value=new_wikidata_id)
    assert new_id.entity == e
    assert new_id.value == new_wikidata_id
    assert new_id.registry.id == REGISTRY_WIKIDATA


@pytest.mark.django_db
def test_new_ror_identifier_from_record(registries, mocker):
    print("Testing new wikidata identifier creation from record.")
    e = EntityFactory.create()
    i_wikidata = IdentifierFactory.create(
        registry_id=REGISTRY_WIKIDATA, entity=e
    )
    new_ror_id = "0aaaazezb"
    with pytest.raises(ObjectDoesNotExist):
        Identifier.objects.get(value=new_ror_id)

    mock_data = pd.DataFrame(
        [
            {
                "id": e.id,
                "name": e.name,
                "ror_id": None,
                "ror_wikidata_id": None,
                "wikidata_id": i_wikidata.value,
                "wikidata_ror_id": new_ror_id,
            }
        ]
    )
    mocker.patch(
        "tsosi.data.enrichment.database_related.entities_with_identifier_data",
        return_value=mock_data,
    )

    new_identifiers_from_records(REGISTRY_ROR)
    new_id = Identifier.objects.get(value=new_ror_id)
    assert new_id.entity == e
    assert new_id.value == new_ror_id
    assert new_id.registry.id == REGISTRY_ROR


@pytest.mark.django_db
def test_new_identifier_from_record_override(registries, mocker):
    print(
        "Testing new identifier creation from record overriding existing one."
    )
    e = EntityFactory.create()
    i_ror = IdentifierFactory.create(entity=e, registry_id=REGISTRY_ROR)
    i_wikidata = IdentifierFactory.create(
        entity=e, registry_id=REGISTRY_WIKIDATA, value="Q12345678"
    )
    new_wikidata_id = "Q12345"

    with pytest.raises(ObjectDoesNotExist):
        Identifier.objects.get(value=new_wikidata_id)

    mock_data = pd.DataFrame(
        [
            {
                "id": e.id,
                "name": e.name,
                "ror_id": i_ror.value,
                "ror_wikidata_id": new_wikidata_id,
                "wikidata_id": i_wikidata.id,
                "wikidata_ror_id": i_ror.value,
            }
        ]
    )
    mocker.patch(
        "tsosi.data.enrichment.database_related.entities_with_identifier_data",
        return_value=mock_data,
    )

    new_identifiers_from_records(REGISTRY_WIKIDATA)
    new_id = Identifier.objects.get(value=new_wikidata_id)
    assert new_id.entity == e
    assert new_id.value == new_wikidata_id
    assert new_id.registry.id == REGISTRY_WIKIDATA

    i_wikidata = Identifier.objects.get(pk=i_wikidata.pk)
    assert i_wikidata.entity is None


@pytest.mark.django_db
def test_new_identifier_from_record_ignore(registries, mocker):
    print("Testing ignored new identifier creation from record.")
    e = EntityFactory.create()
    i_ror = IdentifierFactory.create(entity=e, registry_id=REGISTRY_ROR)
    i_wikidata = IdentifierFactory.create(
        entity=e, registry_id=REGISTRY_WIKIDATA, value="Q12345678"
    )
    new_ror_id = "0aaaazezb"

    with pytest.raises(ObjectDoesNotExist):
        Identifier.objects.get(value=new_ror_id)

    mock_data = pd.DataFrame(
        [
            {
                "id": e.id,
                "name": e.name,
                "ror_id": i_ror.value,
                "ror_wikidata_id": i_wikidata.value,
                "wikidata_id": i_wikidata.id,
                "wikidata_ror_id": new_ror_id,
            }
        ]
    )
    mocker.patch(
        "tsosi.data.enrichment.database_related.entities_with_identifier_data",
        return_value=mock_data,
    )

    new_identifiers_from_records(REGISTRY_ROR)

    with pytest.raises(ObjectDoesNotExist):
        Identifier.objects.get(value=new_ror_id)

    i_ror = Identifier.objects.get(pk=i_ror.pk)
    assert i_ror.entity == e
