import pandas as pd
from tsosi.data.ingestion.entity_matching import match_entities
from tsosi.models.transfer import (
    MATCH_CRITERIA_SAME_NAME_COUNTRY,
    MATCH_CRITERIA_SAME_NAME_ONLY,
    MATCH_CRITERIA_SAME_NAME_URL,
    MATCH_CRITERIA_SAME_PID,
)

to_match = pd.DataFrame.from_records(
    [
        # Match on ROR ID
        {
            "name": "DOAJ",
            "country": None,
            "website": None,
            "ror_id": "05amyt365",
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": "1",
            "expected_match_criteria": MATCH_CRITERIA_SAME_PID,
        },
        # Match on Wikidata ID
        {
            "name": "DOAJ",
            "country": None,
            "website": None,
            "ror_id": None,
            "wikidata_id": "Q1227538",
            "custom_id": None,
            "expected_entity_id": "1",
            "expected_match_criteria": MATCH_CRITERIA_SAME_PID,
        },
        # Match on Name & country
        {
            "name": "Ghent University",
            "country": "BE",
            "website": None,
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": "2",
            "expected_match_criteria": MATCH_CRITERIA_SAME_NAME_COUNTRY,
        },
        # Match on Name & website
        {
            "name": "Ghent University",
            "country": None,
            "website": "https://www.ugent.be",
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": "2",
            "expected_match_criteria": MATCH_CRITERIA_SAME_NAME_URL,
        },
        # Match on Name of a merged entity
        {
            "name": "Ghent University Library",
            "country": None,
            "website": None,
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": "2",
            "expected_match_criteria": MATCH_CRITERIA_SAME_NAME_ONLY,
        },
        # Match on nothing, because the corresponding name doesn't have a country
        {
            "name": "Ghent University Library",
            "country": "BE",
            "website": None,
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": None,
            "expected_match_criteria": None,
        },
        # Match on nothing
        {
            "name": "University XX",
            "country": "FR",
            "website": None,
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "expected_entity_id": None,
            "expected_match_criteria": None,
        },
    ]
)

base_entities = pd.DataFrame.from_records(
    [
        {
            "id": "1",
            "name": "Directory of Open Access Journals",
            "country": "DK",
            "website": "https://doaj.org",
            "ror_id": None,
            "wikidata_id": "Q1227538",
            "custom_id": None,
            "merged_with_id": None,
        },
        {
            "id": "1",
            "name": "Directory of Open Access Journals",
            "country": "DK",
            "website": "https://doaj.org",
            "ror_id": "05amyt365",
            "custom_id": None,
            "wikidata_id": None,
            "merged_with_id": None,
        },
        {
            "id": "2",
            "name": "Ghent University",
            "country": "BE",
            "website": "https://www.ugent.be",
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
        },
        {
            "id": "3",
            "name": "Ghent University Library",
            "country": None,
            "website": None,
            "ror_id": None,
            "wikidata_id": None,
            "custom_id": None,
            "merged_with_id": "2",
        },
    ]
)


def test_match_entities():
    print("Testing match_entities")
    test = to_match.copy(deep=True)
    match_entities(test, base_entities, use_merged_id=True)

    equals = test["entity_id"].eq(test["expected_entity_id"])
    assert equals.all()

    equals = test["match_criteria"].eq(test["expected_match_criteria"])
    assert equals.all()
