from typing import Generic, TypeVar

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from tsosi.models import (
    DataLoadSource,
    Entity,
    EntityRequest,
    Identifier,
    IdentifierEntityMatching,
    IdentifierRequest,
    IdentifierVersion,
    Transfer,
)
from tsosi.models.identifier import MATCH_CRITERIA_FROM_INPUT
from tsosi.models.static_data import MATCH_SOURCE_MANUAL, REGISTRY_ROR

T = TypeVar("T")


class BaseTypingFactory(DjangoModelFactory, Generic[T]):
    """
    Factory boy does not provide correct type hints of created objects.
    For ex: the type of `sub = SubmissionFactory()` is `SubmissionFactory` when we want
    `Submission`

    This base class enables correct type hints when instantiating new objects
    using the `create()` method.
    Ex: `sub = SubmissionFactory.create()` will have the correct type: `Submission`.
    """

    @classmethod
    def create(cls, **kwargs) -> T:
        return super().create(**kwargs)

    @classmethod
    def build(cls, **kwargs) -> T:
        return super().build(**kwargs)


class EntityFactory(BaseTypingFactory[Entity]):
    class Meta:
        model = Entity

    raw_name = Faker("company")
    raw_country = Faker("country_code")
    raw_website = Faker("url")
    name = Faker("company")
    country = Faker("country_code")
    website = Faker("url")


class EntityRequestFactory(BaseTypingFactory[EntityRequest]):
    class Meta:
        model = EntityRequest

    entity = SubFactory(EntityFactory)


class IdentifierFactory(BaseTypingFactory[Identifier]):
    class Meta:
        model = Identifier

    registry_id = REGISTRY_ROR
    value = Faker("ean8")
    entity = SubFactory(EntityFactory)


class IdentifierRequestFactory(BaseTypingFactory[IdentifierRequest]):
    class Meta:
        model = IdentifierRequest

    identifier = SubFactory(IdentifierFactory)


class IdentifierVersionFactory(BaseTypingFactory[IdentifierVersion]):
    class Meta:
        model = IdentifierVersion

    identifier = SubFactory(IdentifierFactory)
    value = Faker("json")


class DataLoadSourceFactory(BaseTypingFactory[DataLoadSource]):
    class Meta:
        model = DataLoadSource

    data_source_id = "pci"
    data_load_name = "test_load"
    date_data_obtained = Faker("date")


class TransferFactory(BaseTypingFactory[Transfer]):
    class Meta:
        model = Transfer

    data_load_source = SubFactory(DataLoadSourceFactory)
    date_payment_recipient = Faker("date")
    emitter = SubFactory(EntityFactory)
    recipient = SubFactory(EntityFactory)
    agent = SubFactory(EntityFactory)
    raw_data = Faker(
        "json",
        data_columns={"amount": "pyint", "emitter": "company", "url": "url"},
    )
    original_id = Faker("pyint")
    original_amount_field = "amount"


class IdentifierEntityMatchingFactory(
    BaseTypingFactory[IdentifierEntityMatching]
):
    class Meta:
        model = IdentifierEntityMatching

    entity = SubFactory(EntityFactory)
    identifier = SubFactory(IdentifierFactory)
    match_criteria = MATCH_CRITERIA_FROM_INPUT
    match_source = MATCH_SOURCE_MANUAL
