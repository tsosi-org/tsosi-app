from django.dispatch import Signal

# Signal sent when new transferts are created in Database
transferts_created = Signal()
# Signal sent when identifiers are created in Database
identifiers_created = Signal()
# Signal sent when identifier records are fetched from the registry
identifiers_fetched = Signal()
