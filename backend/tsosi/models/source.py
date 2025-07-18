from django.db import models

from .utils import TimestampedModel


class DataSource(TimestampedModel):
    id = models.CharField(max_length=64, primary_key=True)


class DataLoadSource(TimestampedModel):
    """
    Model storing the performed data load.
    It's used to prevent data duplication when ingesting new datasets.
    """

    data_source = models.ForeignKey(
        DataSource, null=False, on_delete=models.CASCADE
    )
    data_load_name = models.CharField(max_length=128)
    year = models.IntegerField(null=True)
    full_data = models.BooleanField(default=False)
    date_data_obtained = models.DateField(null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["data_source", "year"],
                condition=models.Q(full_data=True),
                name="unique_full_data_per_source_year",
                nulls_distinct=True,
            )
        ]
