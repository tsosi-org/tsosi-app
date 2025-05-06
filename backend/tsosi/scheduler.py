from django.db import transaction
from django_celery_beat.models import PeriodicTask, PeriodicTasks
from django_celery_beat.schedulers import DatabaseScheduler, info


class DatabaseSchedulerWithCleanup(DatabaseScheduler):
    """
    This scheduler is used to delete all tasks that are not present
    in the loaded schedule.
    Without it, obsolete tasks are never wiped out from the database.
    """

    def setup_schedule(self):
        schedule = self.app.conf.beat_schedule
        with transaction.atomic():
            num, _ = (
                PeriodicTask.objects.filter(task__startswith="tsosi.")
                .exclude(name__in=schedule.keys())
                .delete()
            )
            info(f"Removed {num} obsolete periodic tasks.")
            if num > 0:
                PeriodicTasks.update_changed()
        super().setup_schedule()
