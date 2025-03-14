from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from .entity import Entity


class Analytic(models.Model):
    """
    Stores regularly computed aggregated data.
    This is used by graphs among other applications.
    """

    recipient = models.ForeignKey(Entity, on_delete=models.CASCADE)
    country = models.CharField(
        max_length=2,
        null=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(2)],
    )
    year = models.IntegerField()
    data = models.JSONField()
