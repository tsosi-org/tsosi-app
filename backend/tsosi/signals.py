from django.dispatch import Signal

from .data.signals import (
    identifiers_created,
    identifiers_fetched,
    transferts_created,
)
from .tasks import (
    trigger_identifier_data_processing,
    trigger_new_identifier_fetching,
    trigger_post_ingestion_pipeline,
    trigger_wiki_data_update,
)

transferts_created.connect(trigger_post_ingestion_pipeline)

identifiers_fetched.connect(trigger_identifier_data_processing)

identifiers_fetched.connect(trigger_wiki_data_update)
identifiers_created.connect(trigger_new_identifier_fetching)
