import asyncio
import logging
import time
from typing import Callable

import redis
from celery import Task, shared_task
from django.dispatch import receiver
from redis.lock import Lock

from .app_settings import app_settings
from .data import enrichment
from .data.currencies import currency_rates
from .data.task_result import TaskResult
from .signals import (
    identifiers_created,
    identifiers_fetched,
    transferts_created,
)

logger = logging.getLogger(__name__)


class TsosiTask(Task):
    """
    Custom Celery task for Tsosi app:
        - It logs error to the `tsosi.data` logger
        - If the task's return object is a TaskResult, it will re-schedule
        the task if required.
        - It uses a lock to prevent the same task to be processed several times
        in parallel.
    """

    def __call__(self, *args, **kwargs):
        logger.info(f"Running task: {self.name}")
        result = super().__call__(*args, **kwargs)
        if (
            isinstance(result, TaskResult)
            and (result.partial or result.re_schedule)
            and result.countdown is not None
        ):
            self.re_schedule(
                result.countdown,
                msg="Only partial update was performed.",
                args=args,
                kwargs=kwargs,
            )
        return result

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Manually add a log entry to the tsosi data logger when a task fails.
        """
        logger.error(
            f"Celery task failed with exception: {exc}, args: {args}, kwargs: {kwargs}",
            exc_info=einfo,
        )
        return super().on_failure(exc, task_id, args, kwargs, einfo)

    def re_schedule(
        self,
        countdown: int,
        msg: str | None = None,
        args: tuple = tuple(),
        kwargs: dict = {},
    ):
        log_info = f"Rescheduling task: {self.name} in {countdown} seconds."
        if msg is not None:
            log_info += f"\n{msg}"
        logger.info(log_info)
        self.apply_async(args=args, kwargs=kwargs, countdown=countdown)


redis_client = redis.StrictRedis(
    host=app_settings.REDIS_HOST,
    port=app_settings.REDIS_PORT,
    db=app_settings.REDIS_DB,
)


class TsosiLockedTask(TsosiTask):
    """
    Same as TsosiTask with an additional lock used to prevent the same task
    from being run concurrently.
    This class should be used for every task involving external data fetching.
    """

    def __call__(self, *args, **kwargs):
        lock_name = f"{self.name}_lock"

        lock: Lock = redis_client.lock(
            lock_name, timeout=10 * 60, blocking=False
        )
        result = None
        try:
            if lock.acquire():
                result = super().__call__(*args, **kwargs)
            else:
                self.re_schedule(
                    countdown=30,
                    msg=f"Task {self.name} is already running.",
                    args=args,
                    kwargs=kwargs,
                )
        finally:
            if lock.owned():
                lock.release()
            return result


@shared_task(bind=True, base=TsosiLockedTask)
def update_logos(self: TsosiLockedTask):
    return enrichment.update_logos()


@shared_task(bind=True, base=TsosiLockedTask)
def update_wikipedia_extract(self: TsosiLockedTask):
    return enrichment.update_wikipedia_extract()


@shared_task(bind=True, base=TsosiLockedTask)
def currency_rates_workflow(self):
    return currency_rates.currency_rates_workflow()


@shared_task(bind=True, base=TsosiTask)
def update_wiki_data(self: TsosiTask):
    """
    Pipeline to fetch wikipedia extract and wikimedia files.
    """
    update_wikipedia_extract.delay()
    update_logos.delay()
    return TaskResult(partial=False)


@shared_task(bind=True, base=TsosiLockedTask)
def fetch_empty_identifier_records(self):
    return enrichment.fetch_empty_identifier_records()


@shared_task(bind=True, base=TsosiTask)
def post_ingestion_pipeline(self):
    """
    Pipeline to be run after ingesting new records:
    1 - Update CLC fields
    2 - Launch identifier setup
    """
    tasks: list[Callable] = [
        enrichment.update_transfert_date_clc,
        enrichment.update_entity_roles_clc,
    ]
    results = [task() for task in tasks]
    fetch_empty_identifier_records.delay()
    currency_rates_workflow.delay()
    return TaskResult(partial=False, data_modified=True)


@shared_task(bind=True, base=TsosiTask)
def process_identifier_data(self):
    """
    Pipeline to process the identifier data when some identifiers are
    updated.
    """
    enrichment.new_identifiers_from_records()
    enrichment.update_entity_from_pid_records()
    update_wiki_data.delay()


@shared_task(bind=True, base=TsosiLockedTask)
def identifier_update(self):
    """
    Periodic task to update identifier records.
    """
    pass


## Signal handlers to trigger related tasks
@receiver(transferts_created)
def trigger_post_ingestion_pipeline(sender, **kwargs):
    logger.info("Triggering post-ingestion pipeline.")
    post_ingestion_pipeline.delay()


@receiver(identifiers_fetched)
def trigger_identifier_data_processing(sender, **kwargs):
    logger.info("Triggering identifier data processing.")
    process_identifier_data.delay()


@receiver(identifiers_created)
def trigger_new_identifier_fetching(sender, **kwargs):
    logger.info("Triggering new identifier fetching.")
