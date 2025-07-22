from datetime import UTC, datetime

import pandas as pd
import pytest
from tsosi.data.enrichment.database_related import (
    ingest_entity_identifier_relations,
)
from tsosi.models import Identifier, IdentifierEntityMatching
from tsosi.models.identifier import MATCH_CRITERIA_FROM_WIKIDATA
from tsosi.models.static_data import REGISTRY_ROR
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC

from ..factories import (
    EntityFactory,
    IdentifierEntityMatchingFactory,
    IdentifierFactory,
)


@pytest.mark.django_db
def test_rels_ingestion(registries):
    print("Testing the ingestion of entity <-> identifier relations.")
    e_0 = EntityFactory.create()
    e_1 = EntityFactory.create()
    e_2 = EntityFactory.create()
    e_3 = EntityFactory.create()
    e_4 = EntityFactory.create()
    e_5 = EntityFactory.create()

    i_0 = IdentifierFactory.create(
        value="i0", entity=e_0, registry_id=REGISTRY_ROR
    )
    i_1 = IdentifierFactory.create(
        value="i1", entity=e_1, registry_id=REGISTRY_ROR
    )
    i_2 = IdentifierFactory.create(
        value="i2", entity=e_2, registry_id=REGISTRY_ROR
    )
    i_3 = IdentifierFactory.create(
        value="i3", entity=e_3, registry_id=REGISTRY_ROR
    )

    i_m_0 = IdentifierEntityMatchingFactory.create(entity=e_0, identifier=i_0)
    i_m_1 = IdentifierEntityMatchingFactory.create(entity=e_1, identifier=i_1)
    i_m_2 = IdentifierEntityMatchingFactory.create(entity=e_2, identifier=i_2)
    i_m_3 = IdentifierEntityMatchingFactory.create(entity=e_3, identifier=i_3)

    rel_data = pd.DataFrame(
        [
            {
                "entity_id": e_0.id,
                "identifier_value": i_0.value,
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
            {
                "entity_id": e_2.id,
                "identifier_value": i_1.value,
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
            {
                "entity_id": e_3.id,
                "identifier_value": i_1.value,
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
            {
                "entity_id": e_4.id,
                "identifier_value": "i4",
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
            {
                "entity_id": e_1.id,
                "identifier_value": i_2.value,
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
            {
                "entity_id": e_5.id,
                "identifier_value": "i4",
                "match_source": MATCH_SOURCE_AUTOMATIC,
                "match_criteria": MATCH_CRITERIA_FROM_WIKIDATA,
            },
        ],
    )

    date_update = datetime.now(UTC)
    ingest_entity_identifier_relations(rel_data, REGISTRY_ROR, date_update)

    e_0.refresh_from_db()
    e_1.refresh_from_db()
    e_2.refresh_from_db()
    e_3.refresh_from_db()
    e_4.refresh_from_db()
    e_5.refresh_from_db()

    i_0.refresh_from_db()
    i_1.refresh_from_db()
    i_2.refresh_from_db()
    i_3.refresh_from_db()
    i_4 = Identifier.objects.get(value="i4")

    assert i_0.entity == e_0
    assert i_1.entity == e_2
    assert i_2.entity == e_1
    assert i_3.entity is None
    assert i_4.entity == e_4

    assert e_3.merged_with == e_2
    assert e_5.merged_with == e_4

    # Check IdentifierEntityMatching creation
    i_m_0.refresh_from_db()
    i_m_1.refresh_from_db()
    i_m_2.refresh_from_db()
    i_m_3.refresh_from_db()

    i_m_0s = IdentifierEntityMatching.objects.filter(identifier=i_0)
    assert len(i_m_0s) == 1
    assert i_m_0s[0] == i_m_0
    assert i_m_0.date_end is None

    i_m_1s = IdentifierEntityMatching.objects.filter(identifier=i_1).order_by(
        "date_start"
    )
    assert len(i_m_1s) == 2
    assert i_m_1s[0] == i_m_1
    assert i_m_1.date_end == date_update
    assert i_m_1s[1].date_end is None
    assert i_m_1s[1].entity == e_2

    i_m_2s = IdentifierEntityMatching.objects.filter(identifier=i_2).order_by(
        "date_start"
    )
    assert len(i_m_2s) == 2
    assert i_m_2s[0] == i_m_2
    assert i_m_2.date_end == date_update
    assert i_m_2s[1].date_end is None
    assert i_m_2s[1].entity == e_1

    i_m_3s = IdentifierEntityMatching.objects.filter(identifier=i_3).order_by(
        "date_start"
    )
    assert len(i_m_3s) == 1
    assert i_m_3s[0] == i_m_3
    assert i_m_3.date_end == date_update
    assert i_m_3.entity == e_3

    i_m_4 = IdentifierEntityMatching.objects.get(identifier=i_4)
    assert i_m_4.date_end is None
    assert i_m_4.entity == e_4
