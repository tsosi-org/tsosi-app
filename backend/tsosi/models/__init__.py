from .analytics import Analytic
from .currency import Currency, CurrencyRate
from .entity import Entity, EntityRequest, EntityType, InfrastructureDetails
from .identifier import (
    Identifier,
    IdentifierEntityMatching,
    IdentifierRequest,
    IdentifierVersion,
    Registry,
)
from .source import DataLoadSource, DataSource
from .transfer import Transfer, TransferEntityMatching


def empty_db():
    """
    Delete all rows of all TSOSI models.
    """
    print("Emptying database...")
    Transfer.objects.all().delete()
    Identifier.objects.all().delete()
    Entity.objects.all().delete()
    Registry.objects.all().delete()
    Currency.objects.all().delete()
    DataSource.objects.all().delete()
    print("Database emptied.")
