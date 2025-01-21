from django.core.exceptions import ObjectDoesNotExist

from .entity import Entity
from .identifier import Identifier, Registry

REGISTRY_ROR = "ror"
REGISTRY_WIKIDATA = "wikidata"

PID_REGISTRIES = [
    Registry(
        id=REGISTRY_ROR,
        name="Research Organization Registry",
        website="https://ror.org",
        link_template="https://ror.org/{id}",
    ),
    Registry(
        id=REGISTRY_WIKIDATA,
        name="Wikidata",
        website="https://www.wikidata.org",
        link_template="https://www.wikidata.org/wiki/{id}",
    ),
]


def create_pid_registries():
    """
    Create the PID registries.
    """
    existing_registries = Registry.objects.all()
    ids = [r.id for r in existing_registries]
    for r in PID_REGISTRIES:
        if r.id in ids:
            continue
        r.save()


SUPPORTED_INFRASTRUCTURES = [
    {
        "id": "doaj",
        "pid": {"registry_id": REGISTRY_ROR, "value": "05amyt365"},
        "entity": {
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/doaj-directory-of-open-access-journals",
            "posi_url": "https://blog.doaj.org/2022/10/06/doaj-commits-to-the-principles-of-open-scholarly-infrastructure-posi/",
            "is_scoss_awarded": True,
        },
    },
    {
        "id": "doab",
        "pid": {"registry_id": REGISTRY_ROR, "value": "01q0bmy69"},
        "entity": {
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/directory-of-open-access-books",
            "posi_url": "https://oapen.hypotheses.org/524",
            "is_scoss_awarded": True,
        },
    },
    {
        "id": "operas",
        "pid": {"registry_id": REGISTRY_ROR, "value": "00rfexj26"},
        "entity": {
            "infra_finder_url": None,
            "posi_url": "https://operas-eu.org/principles-of-open-scholarly-infrastructure-posi/",
            "is_scoss_awarded": False,
        },
    },
    {
        "id": "pci",
        "pid": {"registry_id": REGISTRY_ROR, "value": "0315saa81"},
        "entity": {
            "infra_finder_url": "https://infrafinder.investinopen.org/solutions/peer-community-in",
            "posi_url": "https://peercommunityin.org/2024/04/11/posi/",
            "is_scoss_awarded": False,
        },
    },
    {
        "id": "scipost",
        "pid": {"registry_id": REGISTRY_WIKIDATA, "value": "Q52663237"},
        "entity": {
            "infra_finder_url": None,
            "posi_url": "https://scipost.org/posi",
            "is_scoss_awarded": True,
        },
    },
]


def update_infrastructures():
    """
    Update the static data of the supported infrastructures.
    """
    to_update = []
    for infra in SUPPORTED_INFRASTRUCTURES:
        try:
            identifier = Identifier.objects.get(**infra["pid"])
        except ObjectDoesNotExist:
            continue
        entity = Entity(**infra["entity"])
        entity.id = identifier.entity_id
        to_update.append(entity)
    fields = ["infra_finder_url", "posi_url", "is_scoss_awarded"]
    Entity.objects.bulk_update(to_update, fields=fields)
