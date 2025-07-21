from .ingestion.core import ingest
from .preparation.scipost.configs import get_api_config


def refresh_scipost_data():
    config = get_api_config()
    ingestion_config = config.generate_data_ingestion_config()
    ingest(ingestion_config, send_signals=True)
