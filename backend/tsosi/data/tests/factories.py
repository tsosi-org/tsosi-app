from typing import Generic, TypeVar

from factory import Dict, Faker, SubFactory, post_generation
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice
from tsosi.data.preparation.raw_data_config import DATA_SOURCES
from tsosi.models import (
    Currency,
    DataLoadSource,
    Entity,
    EntityRequest,
    Identifier,
    IdentifierEntityMatching,
    IdentifierRequest,
    IdentifierVersion,
    Transfer,
)
from tsosi.models.date import DATE_PRECISION_CHOICES
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


date_faker = Dict(
    {
        "value": Faker("date"),
        "precision": Faker(
            "random_element", elements=list(DATE_PRECISION_CHOICES.keys())
        ),
    }
)


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

    data_source_id = Faker("random_element", elements=DATA_SOURCES)
    data_load_name = Faker("word")
    date_data_obtained = Faker("date")


class TransferFactory(BaseTypingFactory[Transfer]):
    class Meta:
        model = Transfer

    date_payment_recipient = date_faker
    date_payment_emitter = date_faker
    emitter = SubFactory(EntityFactory)
    recipient = SubFactory(EntityFactory)
    agent = SubFactory(EntityFactory)
    amount = Faker("pyfloat", min_value=100, max_value=10000, right_digits=2)
    currency_id = FuzzyChoice(["USD", "EUR", "GBP"])
    date_invoice = date_faker
    raw_data = Faker(
        "json",
        data_columns={"amount": "pyint", "emitter": "company", "url": "url"},
    )
    original_id = Faker("pyint")
    original_amount_field = "amount"

    @post_generation
    def amounts_clc(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.amounts_clc = extracted
        else:
            self.amounts_clc = {
                "USD": round(self.amount * 1.1, 2),
                "EUR": round(self.amount * 1.2, 2),
                "GBP": round(self.amount * 0.9, 2),
            }
            self.amounts_clc[self.currency_id] = self.amount
        self.save()

    @post_generation
    def data_load_sources(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for data_load_source in extracted:
                self.data_load_sources.add(data_load_source)
        else:
            self.data_load_sources.add(DataLoadSourceFactory.create())

        self.raw_data = {
            dls.data_source_id: self.raw_data
            for dls in self.data_load_sources.all()
        }
        self.save()

    @post_generation
    def currency(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.currency = extracted
        else:
            self.currency = Currency.objects.get_or_create(id=self.currency_id)[
                0
            ]
        self.save()


class IdentifierEntityMatchingFactory(
    BaseTypingFactory[IdentifierEntityMatching]
):
    class Meta:
        model = IdentifierEntityMatching

    entity = SubFactory(EntityFactory)
    identifier = SubFactory(IdentifierFactory)
    match_criteria = MATCH_CRITERIA_FROM_INPUT
    match_source = MATCH_SOURCE_MANUAL
