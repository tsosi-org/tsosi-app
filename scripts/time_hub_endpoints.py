"""
Time the Data Contribution Hub endpoints on the local database (a copy of
prod, see `pull_prod_db.sh`), for the organizations with the most supports,
as a TSOSI team member. Everything, the temporary user included, is rolled
back.

    cd backend && poetry run python manage.py shell < ../scripts/time_hub_endpoints.py

Target: under 1 s each.
"""

import time

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count
from django.test import Client
from django.test.utils import CaptureQueriesContext

from tsosi.models import Entity, Transfer

# Matched on their name, the one with the most supports
NAMES = [
    "KU Leuven",
    "Université de Rennes",
    "EPFL",
    "Université Grenoble Alpes",
    "Couperin",
    "Directory of Open Access Journals",
]
SEARCHES = ["univ", "02feahw73", "open"]


class Rollback(Exception):
    pass


def timed_get(client: Client, url: str) -> str:
    with CaptureQueriesContext(connection) as queries:
        start = time.perf_counter()
        response = client.get(url)
        duration = (time.perf_counter() - start) * 1000
    return (
        f"{response.status_code} {duration:7.0f} ms "
        f"{len(queries.captured_queries):5d} queries "
        f"{len(response.content) // 1024:6d} kB"
    )


try:
    with transaction.atomic():
        staff = get_user_model().objects.create_user(
            username="timing@tsosi.org",
            email="timing@tsosi.org",
            is_staff=True,
        )
        client = Client(HTTP_HOST="localhost")
        client.force_login(staff)
        for name in NAMES:
            entity = (
                Entity.objects.filter(is_active=True, name__icontains=name)
                .annotate(
                    supports=Count("transfer_as_emitter", distinct=True)
                    + Count("transfer_as_recipient", distinct=True)
                    + Count("transfer_as_agent", distinct=True)
                )
                .order_by("-supports")
                .first()
            )
            if entity is None:
                print(f"\n{name}: not found")
                continue
            print(f"\n{entity.name} ({entity.supports} supports)")
            recipient = (
                Transfer.objects.filter(emitter=entity)
                .values_list("recipient_id", flat=True)
                .first()
            )
            base = f"/api/hub/entities/{entity.id}"
            for path in [
                "transfers",
                "declarations",
                "publication-preview",
                "submissions",
                f"matches?recipient_id={recipient or entity.id}"
                "&date_invoice=2024&amount=1000&currency=EUR",
            ]:
                label = path.split("?")[0]
                print(f"  {label:22} {timed_get(client, f'{base}/{path}')}")
        print()
        for query in SEARCHES:
            url = f"/api/hub/organizations?search={query}"
            print(f"  search {query!r:15} {timed_get(client, url)}")
        raise Rollback
except Rollback:
    pass
