from django.db import models

from .entity import Entity
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
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["data_source", "year"],
                condition=models.Q(full_data=True),
                name="unique_full_data_per_source_year",
                nulls_distinct=True,
            )
        ]

    def serialize(self) -> str:
        d = {
            "data_source": self.data_source_id,  # type: ignore
            "data_load_name": self.data_load_name,
            "year": self.year,
            "full_data": self.full_data,
            "date_data_obtained": self.date_data_obtained,
        }
        return "{ " + ", ".join([f"{k}: {v}" for k, v in d.items()]) + " }"

    def stats(self) -> str:
        """return stats about the data load source"""
        from tsosi.models import Transfer

        dls_transfers = self.transfers
        all_transfers = self.entity.transfers.exclude(
            id__in=dls_transfers.values("id")
        )
        merged = dls_transfers.filter(merged_into__isnull=False)
        emitters = dls_transfers.values("emitter").distinct()
        recipients = dls_transfers.values("recipient").distinct()
        agents = dls_transfers.values("agents").distinct()
        msg = f"DataLoadSource {self.id} ({self.data_source_id}):\n"
        msg += (
            f"- Transfers: {dls_transfers.count()} ({merged.count()} merged)\n"
        )
        msg += f"- Emitters: {emitters.count()}\n"
        msg += f"- Agents: {agents.count()}\n"
        msg += f"- Recipients: {recipients.count()}"
        return msg
