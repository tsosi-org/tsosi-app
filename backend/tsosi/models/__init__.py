from .analytics import Analytic
from .currency import Currency, CurrencyRate
from .entity import (
    Entity,
    EntityName,
    EntityRequest,
    EntityType,
    InfrastructureDetails,
)
from .identifier import (
    Identifier,
    IdentifierEntityMatching,
    IdentifierRequest,
    IdentifierVersion,
    Registry,
)
from .source import DataLoadSource, DataSource
from .transfer import Transfer, TransferEntityMatching


def empty_db(full=False):
    """
    Delete all transfer related data.

    :param full:    Empty all TSOSI data tables, including entities,
                    identifiers and currency related data.
    """
    print("Emptying database...")
    Transfer.objects.all().delete()
    DataLoadSource.objects.all().delete()
    Analytic.objects.all().delete()
    if full:
        DataSource.objects.all().delete()
        Identifier.objects.all().delete()
        Entity.objects.all().delete()
        Registry.objects.all().delete()
        Currency.objects.all().delete()
    else:
        Entity.objects.all().update(is_active=False)
    print("Database emptied.")
