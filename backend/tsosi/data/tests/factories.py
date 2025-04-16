from typing import Generic, TypeVar

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from tsosi.models import (
    Entity,
    EntityRequest,
    Identifier,
    IdentifierRequest,
    IdentifierVersion,
)

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
