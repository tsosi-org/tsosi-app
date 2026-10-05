from tsosi.data.infra_lists import fetch_barcelona_declaration
from tsosi.models import Entity

from .ingestion.core import ingest
from .preparation.scipost.configs import get_api_config


def refresh_scipost_data():
    config = get_api_config()
    ingestion_config = config.generate_data_ingestion_config()
    ingest(ingestion_config, send_signals=True)


def refresh_barcelona_data():
    """
    Update the Barcelona Declaration status for all entities in the database.
    """
    ror_ids = [e.ror_id for e in fetch_barcelona_declaration() if e.ror_id]
    Entity.objects.filter(identifiers__value__in=ror_ids).update(
        is_barcelona=True
    )
