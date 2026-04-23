import re

import pandas as pd
from tsosi.data.pid_registry.ror import ROR_ID_REGEX
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
    barcelone_declaration_url = "https://barcelona-declaration.org/downloads/barcelonadeclaration_signatories_supporters.csv"
    df = pd.read_csv(barcelone_declaration_url, encoding="utf-8")
    ror_ids = [
        *filter(
            lambda x: isinstance(x, str) and re.match(ROR_ID_REGEX, x),
            df["ror"].str.replace("https://ror.org/", "").unique().tolist(),
        )
    ]
    Entity.objects.filter(identifiers__value__in=ror_ids).update(
        is_barcelona=True
    )
