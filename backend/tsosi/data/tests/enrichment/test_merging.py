from datetime import UTC, datetime

import pandas as pd
import pytest
from tsosi.data.enrichment.merging import merge_entities
from tsosi.data.exceptions import DataException
from tsosi.models import (
    DataLoadSource,
    Entity,
    Transfer,
    TransferEntityMatching,
)
from tsosi.models.transfer import MATCH_CRITERIA_MERGED
from tsosi.models.utils import MATCH_SOURCE_AUTOMATIC

from ..factories import EntityFactory, TransferFactory


@pytest.mark.django_db
def test_merging(datasources):
    print("Testing merging process.")
    e_1 = EntityFactory.create(
        raw_country=None,
        raw_website=None,
        description=None,
        short_name=None,
    )
    e_merged_1 = EntityFactory.create(
        raw_name="Entity",
        raw_country="FR",
        raw_website="https://test.example",
        description="my_desc",
        short_name="E",
    )
    t_e_1 = TransferFactory.create(emitter=e_merged_1)
    t_e_2 = TransferFactory.create(emitter=e_merged_1)
    t_r = TransferFactory.create(recipient=e_merged_1)
    t_a = TransferFactory.create(agent=e_merged_1)

    merge_criteria = "Test merge"
    merge_data = pd.DataFrame(
        [
            {
                "entity_id": e_merged_1.id,
                "merged_with_id": e_1.id,
                "merged_criteria": merge_criteria,
                "match_criteria": MATCH_CRITERIA_MERGED,
                "match_source": MATCH_SOURCE_AUTOMATIC,
            }
        ]
    )

    merge_entities(merge_data, datetime.now(UTC))
    e_1 = Entity.objects.get(id=e_1.id)
    e_merged_1 = Entity.objects.get(id=e_merged_1.id)
    # Check static data filling when null
    assert e_1.raw_name != e_merged_1.raw_name
    assert e_1.raw_country == e_merged_1.raw_country
    assert e_1.raw_website == e_merged_1.raw_website
    assert e_1.description == e_merged_1.description
    assert e_1.short_name == e_merged_1.short_name

    # Check merging related data
    assert e_merged_1.merged_with == e_1
    assert e_merged_1.merged_criteria == merge_criteria
    assert not e_merged_1.is_active

    # Check transfer entity update
    t_e_1 = Transfer.objects.get(id=t_e_1.id)
    t_e_2 = Transfer.objects.get(id=t_e_2.id)
    t_r = Transfer.objects.get(id=t_r.id)
    t_a = Transfer.objects.get(id=t_a.id)

    assert t_e_1.emitter == e_1
    assert t_e_2.emitter == e_1
    assert t_r.recipient == e_1
    assert t_a.agent == e_1

    # Check TransfertEntityMatching creation
    t_e_m = TransferEntityMatching.objects.get(transfer=t_e_1)
    assert t_e_m.entity == e_1
    assert t_e_m.transfer_entity_type == "emitter"

    t_r_m = TransferEntityMatching.objects.get(transfer=t_r)
    assert t_r_m.entity == e_1
    assert t_r_m.transfer_entity_type == "recipient"

    t_a_m = TransferEntityMatching.objects.get(transfer=t_a)
    assert t_a_m.entity == e_1
    assert t_a_m.transfer_entity_type == "agent"


@pytest.mark.django_db
def test_self_merging():
    """Self merging inputs should be discarded so nothing happens."""
    print("Testing merging checks")
    merge_data = pd.DataFrame(
        [
            {
                "entity_id": "1",
                "merged_with_id": "1",
                "merged_criteria": "Test merge",
                "match_criteria": MATCH_CRITERIA_MERGED,
                "match_source": MATCH_SOURCE_AUTOMATIC,
            }
        ]
    )
    merge_entities(merge_data, datetime.now(UTC))


@pytest.mark.django_db
def test_multi_merging():
    """Merging the same entity with multiple targets."""
    print("Testing merging checks")
    merge_data = pd.DataFrame(
        [
            {
                "entity_id": "1",
                "merged_with_id": "2",
                "merged_criteria": "Test merge",
                "match_criteria": MATCH_CRITERIA_MERGED,
                "match_source": MATCH_SOURCE_AUTOMATIC,
            },
            {
                "entity_id": "1",
                "merged_with_id": "3",
                "merged_criteria": "Test merge",
                "match_criteria": MATCH_CRITERIA_MERGED,
                "match_source": MATCH_SOURCE_AUTOMATIC,
            },
        ]
    )

    with pytest.raises(DataException):
        merge_entities(merge_data, datetime.now(UTC))
