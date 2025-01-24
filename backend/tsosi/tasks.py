import logging

from celery import Task, shared_task

from .data import enrichment
from .data.currencies import currency_rates
from .data.enrichment import TaskResult

logger = logging.getLogger("tsosi.data")


class TsosiTask(Task):
    """
    Custom Celery task for Tsosi app:
        - It logs error to the `tsosi.data` logger
        - If the task's return object is a TaskResult, it will re-schedule
        the task if required.
    """

    def __call__(self, *args, **kwargs):
        result = super().__call__(*args, **kwargs)
        if isinstance(result, TaskResult) and result.partial:
            self.apply_async(
                args=args, kwargs=kwargs, countdown=result.countdown
            )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Manually add a log entry to the tsosi data logger when a task fails.
        """
        logger.error(
            f"Celery task failed with exception: {exc}, args: {args}, kwargs: {kwargs}",
            exc_info=einfo,
        )
        return super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(bind=True, base=TsosiTask)
def new_identifiers_from_records(self):
    enrichment.new_identifiers_from_records()


@shared_task(bind=True, base=TsosiTask)
def update_entity_from_pid_records(self):
    enrichment.update_entity_from_pid_records()


@shared_task(bind=True, base=TsosiTask)
def update_entity_roles_clc(self):
    enrichment.update_entity_roles_clc()


@shared_task(bind=True, base=TsosiTask)
def update_logos(self):
    enrichment.update_logos()


@shared_task(bind=True, base=TsosiTask)
def update_transfert_date_clc(self):
    enrichment.update_transfert_date_clc()


@shared_task(bind=True, base=TsosiTask)
def update_wikipedia_extract(self):
    enrichment.update_wikipedia_extract()


@shared_task(bind=True, base=TsosiTask)
def currency_rates_workflow(self):
    currency_rates.currency_rates_workflow()
