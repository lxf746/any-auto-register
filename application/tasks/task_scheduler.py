"""Task scheduling, retry logic, and lifecycle management."""
from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session, select

from core.datetime_utils import _utcnow
from core.db import TaskModel, engine

from application.tasks.task_repository import (
    ACTIVE_TASK_STATUSES,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_CANCEL_REQUESTED,
    TASK_STATUS_CLAIMED,
    TASK_STATUS_FAILED,
    TASK_STATUS_INTERRUPTED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    TERMINAL_TASK_STATUSES,
    _priority_sort_key,
    append_task_event,
    mutate_task,
    serialize_task,
    task_account_keys,
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


def mark_incomplete_tasks_interrupted() -> None:
    with Session(engine) as session:
        non_terminal = [TASK_STATUS_PENDING] + list(ACTIVE_TASK_STATUSES)
        tasks = session.exec(
            select(TaskModel).where(TaskModel.status.in_(non_terminal))
        ).all()
        task_ids = [task.id for task in tasks]
        for task in tasks:
            task.status = TASK_STATUS_INTERRUPTED
            task.error = task.error or "Task interrupted after service restart"
            task.finished_at = _utcnow()
            task.updated_at = _utcnow()
            session.add(task)
        session.commit()
    for task_id in task_ids:
        append_task_event(
            task_id,
            "Task marked as interrupted after service restart",
            event_type="state",
            level="warning",
        )


def request_cancel(task_id: str) -> Optional[dict[str, Any]]:
    task = mutate_task(
        task_id,
        lambda model: _request_cancel_mutation(model),
    )
    if not task:
        return None
    append_task_event(task_id, "Task cancellation requested", event_type="state", level="warning")
    return serialize_task(task)


def _request_cancel_mutation(task: TaskModel) -> None:
    if task.status in TERMINAL_TASK_STATUSES:
        return
    if task.status == TASK_STATUS_PENDING:
        task.status = TASK_STATUS_CANCELLED
        task.finished_at = _utcnow()
        task.error = task.error or "Task cancelled before starting"
    else:
        task.status = TASK_STATUS_CANCEL_REQUESTED


def claim_next_runnable_task(
    *,
    running_platform_counts: dict[str, int] | None = None,
    busy_account_keys: set[str] | None = None,
    max_parallel_per_platform: int = 1,
) -> Optional[dict[str, Any]]:
    running_platform_counts = dict(running_platform_counts or {})
    busy_account_keys = set(busy_account_keys or set())
    with Session(engine) as session:
        pending_tasks = session.exec(
            select(TaskModel)
            .where(TaskModel.status == TASK_STATUS_PENDING)
        ).all()
        pending_tasks = sorted(pending_tasks, key=_priority_sort_key)
        for task in pending_tasks:
            payload = task.get_payload()
            platform = task.platform or str(payload.get("platform", "") or "")
            account_keys = task_account_keys(task.type, payload)
            if platform and running_platform_counts.get(platform, 0) >= max_parallel_per_platform:
                continue
            if account_keys and busy_account_keys.intersection(account_keys):
                continue
            task.status = TASK_STATUS_CLAIMED
            task.started_at = task.started_at or _utcnow()
            task.updated_at = _utcnow()
            session.add(task)
            session.commit()
            return {"id": task.id, "platform": platform, "account_keys": account_keys}
    return None
