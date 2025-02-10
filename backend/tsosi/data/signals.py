from django.dispatch import Signal

# Signal sent when new transferts are created in the database
transferts_created = Signal()
# Signal sent when identifiers are created in the database
identifiers_created = Signal()
# Signal sent when identifier records are fetched from the registry
identifiers_fetched = Signal()
