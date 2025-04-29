from django.dispatch import Signal

from .data.signals import (
    identifiers_created,
    identifiers_fetched,
    transfers_created,
)
from .tasks import (
    trigger_identifier_data_processing,
    trigger_identifier_versions_cleaning,
    trigger_new_identifier_fetching,
    trigger_post_ingestion_pipeline,
)

# New transfers
transfers_created.connect(trigger_post_ingestion_pipeline)
# New identifiers
identifiers_created.connect(trigger_new_identifier_fetching)
# New identifier versions
identifiers_fetched.connect(trigger_identifier_data_processing)
identifiers_fetched.connect(trigger_identifier_versions_cleaning)
