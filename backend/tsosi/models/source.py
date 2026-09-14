import logging

from django.db import models
from django.db.models import Count
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .entity import Entity
from .utils import TimestampedModel

logger = logging.getLogger(__name__)


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

        from .transfer import Transfer

        dls_transfers = self.transfers
        all_transfers = self.entity.transfers

        def new_participants(field: str):
            """
            Distinct ``field`` entities whose support is exclusive to this
            data load: any entity that also appears (in that role) on a
            transfer not linked to this source is excluded.
            """
            with_other_support = (
                Transfer.objects.filter(
                    **{f"{field}__in": dls_transfers.values(field)}
                )
                .exclude(pk__in=dls_transfers.values("pk"))
                .values(field)
            )
            return (
                dls_transfers.exclude(**{f"{field}__in": with_other_support})
                .values(field)
                .distinct()
            )

        merged = dls_transfers.filter(merged_into__isnull=False)
        new_emitters = new_participants("emitter")
        total_emitters = all_transfers.values("emitter").distinct()
        new_recipients = new_participants("recipient")
        total_recipients = all_transfers.values("recipient").distinct()
        new_agents = new_participants("agents")
        total_agents = all_transfers.values("agents").distinct()
        msg = f"DataLoadSource {self.id} ({self.data_source_id}):\n"
        msg += (
            f"Transfers: {dls_transfers.count() - merged.count()} new (out of {all_transfers.count()})\n"
        )
        msg += f"Emitters: {new_emitters.count()} new (out of {total_emitters.count()})\n"
        msg += f"Agents: {new_agents.count() - 1} new (out of {total_agents.count() - 1})\n"
        msg += f"Recipients: {new_recipients.count()} new (out of {total_recipients.count()})"
        return msg


@receiver(pre_delete, sender=DataLoadSource)
def handle_dls_deletion(sender, instance, using, **kwargs) -> None:
    """
    Remove this source's raw payload from merged transfers that still have two other sources.
    Then remove all other transfers linked to this source.
    """
    from .transfer import Transfer

    transfer_ids = instance.transfers.values("pk")
    transfers = (
        Transfer.objects.filter(pk__in=transfer_ids)
        .prefetch_related("data_load_sources")
        .annotate(dls_count=Count("data_load_sources"))
    )
    for transfer in transfers.filter(dls_count__gte=3):
        raw_data = transfer.raw_data
        raw_data.pop(instance.data_source_id, None)
        transfer.raw_data = raw_data
        transfer.save()

    deleted, _ = transfers.filter(dls_count__lt=3).delete()
    logger.info(
        f"Deleted {deleted} transfers linked to DataLoadSource {instance.id}"
    )
