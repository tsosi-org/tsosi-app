import logging
from pathlib import Path
from typing import Callable

import redis
from celery import shared_task
from celery.contrib.django.task import DjangoTask
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger
from redis.lock import Lock

from .app_settings import app_settings
from .data import analytics, enrichment, ingestion
from .data.currencies import currency_rates
from .data.task_result import TaskResult
from .models.static_data import REGISTRY_ROR, REGISTRY_WIKIDATA

# logger = logging.getLogger("tsosi.data")
logger = logging.getLogger(__name__)
task_logger = get_task_logger(__name__)


class TsosiTask(DjangoTask):
    """
    Custom Celery task for Tsosi app:
        - It logs error to the `tsosi.data` logger
        - If the task's return object is a TaskResult, it will re-schedule
        the task if required.
        - It uses a lock to prevent the same task to be processed several times
        in parallel.
    """

    max_retries = 0

    def before_start(self, task_id, args, kwargs):
        super().before_start(task_id, args, kwargs)
        task_logger.info(f"Running task: {self.name}")

    def on_success(self, retval, task_id, args, kwargs):
        super().on_success(retval, task_id, args, kwargs)
        if (
            isinstance(retval, TaskResult)
            and (retval.partial or retval.re_schedule)
            and retval.countdown is not None
        ):
            self.re_schedule(
                retval.countdown,
                msg="Only partial update was performed.",
                args=args,
                kwargs=kwargs,
            )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Manually add a log entry to the tsosi data logger when a task fails.
        """

        task_logger.error(
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
        task_logger.info(log_info)
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
    This class should be used for every task involving database
    records insertion/deletion.
    """

    lock: Lock | None = None

    def before_start(self, task_id, args, kwargs):
        super().before_start(task_id, args, kwargs)
        lock_name = f"{self.name}_lock"

        lock: Lock = redis_client.lock(
            lock_name, timeout=10 * 60, blocking=False
        )
        if not lock.acquire():
            self.re_schedule(
                countdown=10,
                msg=f"Task {self.name} is already running.",
                args=args,
                kwargs=kwargs,
            )
            raise Ignore("Task is already running.")
        self.lock = lock

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        super().after_return(status, retval, task_id, args, kwargs, einfo)
        if self.lock is not None and self.lock.owned():
            self.lock.release()
            self.lock = None


@shared_task(base=TsosiLockedTask)
def ingest_data_file(file_path: str):
    """
    Ingest single data file. Only for testing purposes, `ingest_all` should
    be preferred to avoid concurrency issues.
    """
    return ingestion.ingest_data_file(file_path)


@shared_task(base=TsosiLockedTask)
def ingest_all():
    """
    Ingest all data files present in INGEST_DIR and delay the
    post-ingestion pipeline after all files are ingested.
    """
    folder = app_settings.TO_INGEST_DIR
    files = folder.glob("*.json")
    for f in files:
        _ = ingestion.ingest_data_file(folder / f, send_signals=False)
    ingestion.send_post_ingestion_signals()


@shared_task(base=TsosiLockedTask)
def ingest_test():
    """
    Ingest all data files present in INGEST_DIR and delay the
    post-ingestion pipeline after all files are ingested.
    """
    folder = app_settings.TSOSI_APP_DATA_DIR / "fixtures/prepared_files"
    files = folder.glob("*.json")
    for f in files:
        _ = ingestion.ingest_data_file(folder / f, send_signals=False)
    ingestion.send_post_ingestion_signals()


@shared_task(base=TsosiLockedTask)
def update_logos():
    return enrichment.update_logos()


@shared_task(base=TsosiLockedTask)
def update_wikipedia_extract():
    return enrichment.update_wikipedia_extract()


@shared_task(base=TsosiLockedTask)
def currency_rates_workflow():
    return currency_rates.currency_rates_workflow()


@shared_task(base=TsosiTask)
def update_wiki_data():
    """
    Pipeline to fetch wikipedia extract and wikimedia files.
    """
    update_wikipedia_extract.delay()
    update_logos.delay()


@shared_task(base=TsosiLockedTask)
def fetch_empty_ror_records():
    return enrichment.fetch_empty_identifier_records(REGISTRY_ROR)


@shared_task(base=TsosiTask)
def fetch_empty_wikidata_records():
    return enrichment.fetch_empty_identifier_records(REGISTRY_WIKIDATA)


@shared_task(base=TsosiLockedTask)
def compute_analytics():
    analytics.compute_analytics()


@shared_task(base=TsosiTask)
def post_ingestion_pipeline():
    """
    Pipeline to be run after ingesting new records:
    1 - Update CLC fields
    2 - Launch identifier setup
    """
    tasks: list[Callable] = [
        enrichment.update_transfert_date_clc,
        enrichment.update_entity_roles_clc,
        enrichment.update_infrastructure_metrics,
    ]
    results = [task() for task in tasks]
    currency_rates_workflow.delay()
    compute_analytics.delay()
    return TaskResult(partial=False, data_modified=True)


@shared_task(base=TsosiLockedTask)
def process_identifier_data():
    """
    Pipeline to process the identifier data when some identifiers are
    updated.
    """
    enrichment.update_entity_from_pid_records()
    enrichment.new_identifiers_from_records()


@shared_task(base=TsosiLockedTask)
def identifier_update():
    """
    Periodic task to update identifier records.
    """
    task_logger.info("Not implemented")


## Signal handlers to trigger related tasks
def trigger_post_ingestion_pipeline(sender, **kwargs):
    if not app_settings.TRIGGER_JOBS:
        logger.info("Skipped triggering of post-ingestion pipeline")
        return
    logger.info("Triggering post-ingestion pipeline.")
    post_ingestion_pipeline.delay_on_commit()


def trigger_identifier_data_processing(sender, **kwargs):
    if not app_settings.TRIGGER_JOBS:
        logger.info("Skipped triggering of identifier data processing")
        return
    logger.info("Triggering identifier data processing.")
    process_identifier_data.delay_on_commit()


def trigger_wiki_data_update(sender, **kwargs):
    if not app_settings.TRIGGER_JOBS:
        logger.info("Skipped triggering of wiki related data")
        return
    registry_id = kwargs.get("registry_id")
    if registry_id == REGISTRY_WIKIDATA:
        logger.info("Triggering update of wiki related data.")
        update_wiki_data.delay_on_commit()


def trigger_new_identifier_fetching(sender, **kwargs):
    if not app_settings.TRIGGER_JOBS:
        logger.info("Skipped triggering of new identifier fetching.")
        return
    registries = kwargs.get("registries")
    if isinstance(registries, list):
        logger.info(
            f"Triggering new identifier fetching for registries: {registries}"
        )
        for registry in registries:
            if registry == REGISTRY_ROR:
                fetch_empty_ror_records.delay_on_commit()
            elif registry == REGISTRY_WIKIDATA:
                fetch_empty_wikidata_records.delay_on_commit()
