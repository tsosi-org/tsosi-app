from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from .date import DateField
from .utils import TimestampedModel


class Currency(TimestampedModel):
    id = models.CharField(
        primary_key=True,
        max_length=3,
        validators=[MinLengthValidator(3), MaxLengthValidator(3)],
    )
    name = models.CharField(max_length=64)


class CurrencyRate(models.Model):
    """ """

    id = models.BigAutoField(primary_key=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    value = models.FloatField()
    date = DateField()
