from .analytics import Analytic
from .currency import Currency, CurrencyRate
from .entity import Entity, EntityType
from .identifier import (
    Identifier,
    IdentifierEntityMatching,
    IdentifierVersion,
    Registry,
)
from .source import DataLoadSource, DataSource
from .transfert import Transfert, TransfertEntityMatching


def empty_db():
    """
    Delete all rows of all TSOSI models.
    """
    print("Emptying database...")
    Transfert.objects.all().delete()
    Identifier.objects.all().delete()
    Entity.objects.all().delete()
    Registry.objects.all().delete()
    Currency.objects.all().delete()
    DataSource.objects.all().delete()
    print("Database emptied.")
