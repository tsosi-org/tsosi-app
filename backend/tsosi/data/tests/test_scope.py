import pytest
from rest_framework.test import APIClient
from tsosi.data.enrichment import compute_analytics, update_entity_roles_clc
from tsosi.models import Analytic, Entity, Transfer
from tsosi.models.entity import ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK

from .factories import EntityFactory, TransferFactory


@pytest.fixture
def transfers(datasources) -> dict[str, Transfer]:
    """
    One transfer to a beneficiary in scope, one to a beneficiary to be
    checked, and one to a beneficiary without scope.
    """
    return {
        scope: TransferFactory.create(
            recipient=EntityFactory.create(scope=scope),
            date_clc={"value": "2024-01-01", "precision": "day"},
        )
        for scope in [ENTITY_SCOPE_IN, ENTITY_SCOPE_TO_CHECK, None]
    }


@pytest.mark.django_db
def test_public_transfers(transfers):
    public = transfers[ENTITY_SCOPE_IN]
    TransferFactory.create(recipient=public.recipient, merged_into=public)
    assert list(Transfer.objects.public()) == [public]

    client = APIClient()
    response = client.get("/api/transfers/")
    assert [t["id"] for t in response.json()["results"]] == [str(public.id)]
    for scope in [ENTITY_SCOPE_TO_CHECK, None]:
        url = f"/api/transfers/{transfers[scope].id}/"
        assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_public_entities(transfers):
    update_entity_roles_clc()
    public = transfers[ENTITY_SCOPE_IN]
    assert set(Entity.objects.public()) == {public.emitter, public.recipient}

    client = APIClient()
    for scope in [ENTITY_SCOPE_TO_CHECK, None]:
        transfer = transfers[scope]
        transfer.recipient.refresh_from_db()
        assert not transfer.recipient.is_recipient
        for entity in [transfer.emitter, transfer.recipient]:
            url = f"/api/entities/{entity.id}/"
            assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_analytics_of_public_transfers(transfers):
    compute_analytics()
    recipient_ids = set(Analytic.objects.values_list("recipient_id", flat=True))
    assert recipient_ids == {transfers[ENTITY_SCOPE_IN].recipient_id}
