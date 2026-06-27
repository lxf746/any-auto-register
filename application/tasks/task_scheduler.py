"""Task scheduling, retry logic, and lifecycle management."""
from __future__ import annotations

from typing import Any, Optional

from core.datetime_utils import _utcnow
from core.db import TaskModel

from application.tasks.task_repository import (
    TASK_STATUS_FAILED,
    TASK_STATUS_INTERRUPTED,
    TASK_STATUS_PENDING,
    append_task_event,
    mutate_task,
    serialize_task,
)


def _schedule_retry(task_id: str, *, delay_seconds: int = 0) -> Optional[dict[str, Any]]:
    def _reset_to_pending(task: TaskModel) -> None:
        if task.status not in {TASK_STATUS_FAILED, TASK_STATUS_INTERRUPTED}:
            return
        task.status = TASK_STATUS_PENDING
        task.error = None
        task.started_at = None
        task.finished_at = None
        task.updated_at = _utcnow()

    task = mutate_task(task_id, _reset_to_pending)
    if not task:
        return None
    append_task_event(task_id, f"Task scheduled for retry (delay={delay_seconds}s)", event_type="state")
    return serialize_task(task)


def schedule_retry(task_id: str, *, delay_seconds: int = 0) -> Optional[dict[str, Any]]:
    return _schedule_retry(task_id, delay_seconds=delay_seconds)



