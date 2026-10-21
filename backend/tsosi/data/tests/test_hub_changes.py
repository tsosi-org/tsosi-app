import pytest
from django.contrib.auth import get_user_model

from tsosi.data.hub_changes import format_amount, submission_changes
from tsosi.data.hub_publication import submit_declarations
from tsosi.models import Currency, Membership
from tsosi.models.declaration import (
    DECLARATION_KIND_CONFIRMATION,
    DECLARATION_KIND_EDIT,
    DECLARATION_KIND_MERGE,
    DECLARATION_KIND_NEW,
    DECLARATION_KIND_NOT_DUPLICATE,
    DECLARATION_KIND_REMOVAL,
)
from tsosi.models.entity import ENTITY_SCOPE_IN

from .factories import EntityFactory
from .test_publication import declare, new_values, support


@pytest.fixture
def org(db):
    Currency.objects.get_or_create(id="EUR")
    return EntityFactory.create(name="Uni")


@pytest.fixture
def member(org):
    user = get_user_model().objects.create_user(
        username="member@uni.edu", email="member@uni.edu"
    )
    Membership.objects.create(user=user, entity=org)
    return user


@pytest.fixture
def infra(db):
    return EntityFactory.create(
        name="Infra", scope=ENTITY_SCOPE_IN, is_recipient=True
    )


def test_format_amount():
    assert format_amount(1500, "EUR") == "1,500 EUR"
    assert format_amount(1500.5, "EUR") == "1,500.5 EUR"
    assert format_amount(None, None) == "no amount"


@pytest.mark.django_db
def test_submission_changes(org, member, infra, datasources):
    """The changes table of the submission page in the admin."""
    agent = EntityFactory.create(name="Consortium")
    confirmed = support(org, infra, infra, date="2021")
    removed = support(org, infra, org, date="2022", source="rennes")
    edited = support(org, infra, infra, date="2023")
    merged = support(org, infra, infra, date="2024")
    duplicate = support(org, infra, infra, amount=2000, date="2024")
    declare(org, member, DECLARATION_KIND_CONFIRMATION, confirmed)
    declare(org, member, DECLARATION_KIND_REMOVAL, removed)
    edit = declare(
        org, member, DECLARATION_KIND_EDIT, edited, **new_values(infra, 1200)
    )
    edit.agents.set([agent])
    declare(org, member, DECLARATION_KIND_MERGE, merged, others=[duplicate])
    declare(
        org,
        member,
        DECLARATION_KIND_NOT_DUPLICATE,
        confirmed,
        others=[duplicate],
    )
    first_new = declare(org, member, DECLARATION_KIND_NEW, **new_values(infra))
    second_new = declare(
        org, member, DECLARATION_KIND_NEW, others=[merged], **new_values(infra)
    )
    second_new.other_declarations.set([first_new])
    submission = submit_declarations(org, member)

    rows = {row[0]: row[1:] for row in submission_changes(submission)}
    # Each row: support, currently published, after approval, declared by
    assert rows["Confirmation"][:3] == (
        "2021 · Infra",
        "1,000 EUR",
        "Unchanged, Uni added as a source",
    )
    assert rows["Confirmation"][3].startswith("Infra · ")
    assert rows["Removal"][2] == (
        "Uni removed as a source: the support is deleted, it has no other "
        "source"
    )
    assert rows["Edit"][:3] == (
        "2025 · Infra",
        "1,000 EUR",
        "1,200 EUR via Consortium. The organization's values are published",
    )
    assert rows["Merge"][2] == "One support with: 2024 · Infra · 2,000 EUR"
    assert rows["Not a duplicate"][2] == (
        "Not the same support as: 2024 · Infra · 2,000 EUR"
    )
    # Two new supports: the last one listed wins in the dict
    assert rows["New support"] == (
        "2025 · Infra",
        "-",
        "500 EUR. Not the same support as: 2024 · Infra · 1,000 EUR. Not "
        f"the same support as the new #{first_new.id}",
        "-",
    )
