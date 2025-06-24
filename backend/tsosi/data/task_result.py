from dataclasses import dataclass, field
from typing import Self


@dataclass
class TaskResult:
    # Whether only a subset of the task's target data was processed
    partial: bool
    # Time to wait before re-scheduling the task
    countdown: int | None = field(default=None)
    # Whether the data was modified (any insertion, update or deletion)
    data_modified: bool = field(default=False)
    # Force the task to be re-scheduled
    re_schedule: bool = field(default=False)

    @classmethod
    def from_tasks(cls, *args: Self) -> Self:
        partial = False
        countdown = None
        data_modified = False
        for task_result in args:
            if task_result.partial:
                partial = True
                countdown = (
                    task_result.countdown
                    if countdown is None
                    else max(countdown, task_result.countdown or 0)
                )
            if task_result.data_modified:
                data_modified = True
        return cls(
            partial=partial, countdown=countdown, data_modified=data_modified
        )
