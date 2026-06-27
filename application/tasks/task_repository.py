"""Task persistence, locking, and CRUD operations."""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Optional

from sqlmodel import Session, select, func

from core.base_platform import AccountStatus
from core.datetime_utils import _utcnow, format_local_clock, serialize_datetime
from core.db import AccountModel, TaskEventModel, TaskLog, TaskModel, engine, save_account
from core.db.models import PRIORITY_LEVELS

TASK_TYPE_REGISTER = "register"
TASK_TYPE_ACCOUNT_CHECK = "account_check"
TASK_TYPE_ACCOUNT_CHECK_ALL = "account_check_all"
TASK_TYPE_PLATFORM_ACTION = "platform_action"

TASK_STATUS_PENDING = "pending"
TASK_STATUS_CLAIMED = "claimed"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCEEDED = "succeeded"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_INTERRUPTED = "interrupted"
TASK_STATUS_CANCEL_REQUESTED = "cancel_requested"
TASK_STATUS_CANCELLED = "cancelled"

TERMINAL_TASK_STATUSES = {
    TASK_STATUS_SUCCEEDED,
    TASK_STATUS_FAILED,
    TASK_STATUS_INTERRUPTED,
    TASK_STATUS_CANCELLED,
}
ACTIVE_TASK_STATUSES = {
    TASK_STATUS_CLAIMED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_CANCEL_REQUESTED,
}

_task_locks: dict[str, threading.Lock] = {}
_task_locks_guard = threading.Lock()


def _serialize_datetime(value: datetime | None) -> str | None:
    return serialize_datetime(value)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _serialize_datetime(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _dump_json(data: Any) -> str:
    return json.dumps(data or {}, ensure_ascii=False, default=_json_default)


_PRIORITY_WEIGHTS: dict[str, int] = {"high": 0, "normal": 1, "low": 2}


def _priority_sort_key(task: TaskModel) -> tuple[int, datetime]:
    """Sort key for priority-based task ordering: high > normal > low, then FIFO."""
    return (_PRIORITY_WEIGHTS.get(task.priority, 1), task.created_at)


def task_lock(task_id: str) -> threading.Lock:
    with _task_locks_guard:
        lock = _task_locks.get(task_id)
        if lock is None:
            lock = threading.Lock()
            _task_locks[task_id] = lock
        return lock


def mutate_task(task_id: str, fn: Callable[[TaskModel], None]) -> Optional[TaskModel]:
    with task_lock(task_id):
        with Session(engine) as session:
            task = session.get(TaskModel, task_id)
            if not task:
                return None
            fn(task)
            task.updated_at = _utcnow()
            session.add(task)
            session.commit()
            session.refresh(task)
            if task.status in TERMINAL_TASK_STATUSES:
                with _task_locks_guard:
                    _task_locks.pop(task_id, None)
            return task


def save_task_log(platform: str, email: str, status: str, error: str = "", detail: dict | None = None) -> None:
    with Session(engine) as session:
        log = TaskLog(
            platform=platform,
            email=email,
            status=status,
            error=error,
            detail_json=_dump_json(detail or {}),
        )
        session.add(log)
        session.commit()


def task_result_seed(result: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {"errors": [], "cashier_urls": [], "data": None}
    if result:
        base.update(result)
    return base


def task_account_keys(task_type: str, payload: dict[str, Any]) -> list[str]:
    if task_type in {TASK_TYPE_ACCOUNT_CHECK, TASK_TYPE_PLATFORM_ACTION}:
        account_id = int(payload.get("account_id", 0) or 0)
        if account_id > 0:
            return [f"account:{account_id}"]
    return []


def serialize_task(task: TaskModel) -> dict[str, Any]:
    result = task.get_result()
    progress_total = int(task.progress_total or 0)
    progress_current = int(task.progress_current or 0)
    return {
        "id": task.id,
        "task_id": task.id,
        "type": task.type,
        "platform": task.platform,
        "status": task.status,
        "priority": task.priority,
        "terminal": task.status in TERMINAL_TASK_STATUSES,
        "cancellable": task.status in {TASK_STATUS_PENDING, TASK_STATUS_CLAIMED, TASK_STATUS_RUNNING, TASK_STATUS_CANCEL_REQUESTED},
        "progress": f"{progress_current}/{progress_total}" if progress_total else "0/0",
        "progress_detail": {
            "current": progress_current,
            "total": progress_total,
            "label": f"{progress_current}/{progress_total}" if progress_total else "0/0",
        },
        "success": int(task.success_count or 0),
        "error_count": int(task.error_count or 0),
        "errors": list(result.get("errors", [])),
        "cashier_urls": list(result.get("cashier_urls", [])),
        "data": result.get("data"),
        "result": result,
        "error": task.error,
        "created_at": _serialize_datetime(task.created_at),
        "started_at": _serialize_datetime(task.started_at),
        "finished_at": _serialize_datetime(task.finished_at),
        "updated_at": _serialize_datetime(task.updated_at),
    }


def serialize_event(event: TaskEventModel) -> dict[str, Any]:
    return {
        "id": event.id,
        "task_id": event.task_id,
        "type": event.type,
        "level": event.level,
        "message": event.message,
        "line": f"[{format_local_clock(event.created_at)}] {event.message}",
        "detail": event.get_detail(),
        "created_at": _serialize_datetime(event.created_at),
    }


def append_task_event(task_id: str, message: str, *, event_type: str = "log", level: str = "info", detail: dict | None = None) -> dict[str, Any]:
    with Session(engine) as session:
        event = TaskEventModel(
            task_id=task_id,
            type=event_type,
            level=level,
            message=message,
            detail_json=_dump_json(detail or {}),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
    return serialize_event(event)


def get_task(task_id: str) -> Optional[dict[str, Any]]:
    with Session(engine) as session:
        task = session.get(TaskModel, task_id)
        return serialize_task(task) if task else None


def list_tasks(*, platform: str = "", status: str = "", page: int = 1, page_size: int = 50) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    with Session(engine) as session:
        q = select(TaskModel)
        total_q = select(func.count()).select_from(TaskModel)
        if platform:
            q = q.where(TaskModel.platform == platform)
            total_q = total_q.where(TaskModel.platform == platform)
        if status:
            q = q.where(TaskModel.status == status)
            total_q = total_q.where(TaskModel.status == status)
        q = q.order_by(TaskModel.created_at.desc())
        total = int(session.exec(total_q).one() or 0)
        items = session.exec(q.offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "page": page, "items": [serialize_task(item) for item in items]}


def list_task_events(task_id: str, *, since: int = 0, limit: int = 200) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 500)
    with Session(engine) as session:
        q = (
            select(TaskEventModel)
            .where(TaskEventModel.task_id == task_id)
            .where(TaskEventModel.id > since)
            .order_by(TaskEventModel.id)
            .limit(limit)
        )
        items = session.exec(q).all()
    return [serialize_event(item) for item in items]


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
            return {"id": task.id, "platform": platform, "account_keys": account_keys, "priority": task.priority}
    return None


def create_task(
    *,
    task_type: str,
    platform: str,
    payload: dict[str, Any],
    progress_total: int = 1,
    result_seed: dict[str, Any] | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    if priority not in PRIORITY_LEVELS:
        priority = "normal"
    task_id = f"task_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    task = TaskModel(
        id=task_id,
        type=task_type,
        platform=platform,
        status=TASK_STATUS_PENDING,
        priority=priority,
        payload_json=_dump_json(payload),
        result_json=_dump_json(task_result_seed(result_seed)),
        progress_current=0,
        progress_total=max(int(progress_total or 0), 0),
    )
    with Session(engine) as session:
        session.add(task)
        session.commit()
        session.refresh(task)
    append_task_event(task.id, f"Task created: {task_type}", event_type="state")
    return serialize_task(task)


def create_register_task(payload: dict[str, Any]) -> dict[str, Any]:
    count = max(int(payload.get("count", 1) or 1), 1)
    priority = str(payload.get("priority", "normal") or "normal")
    return create_task(
        task_type=TASK_TYPE_REGISTER,
        platform=str(payload.get("platform", "")),
        payload=payload,
        progress_total=count,
        priority=priority,
    )


def create_account_check_task(account_id: int) -> dict[str, Any]:
    platform = ""
    with Session(engine) as session:
        model = session.get(AccountModel, account_id)
        if model:
            platform = model.platform
    return create_task(
        task_type=TASK_TYPE_ACCOUNT_CHECK,
        platform=platform,
        payload={"account_id": int(account_id)},
        progress_total=1,
    )


def create_account_check_all_task(platform: str = "", limit: int = 50) -> dict[str, Any]:
    return create_task(
        task_type=TASK_TYPE_ACCOUNT_CHECK_ALL,
        platform=platform,
        payload={"platform": platform, "limit": int(limit or 50)},
        progress_total=max(int(limit or 50), 1),
    )


def create_platform_action_task(payload: dict[str, Any]) -> dict[str, Any]:
    priority = str(payload.get("priority", "normal") or "normal")
    return create_task(
        task_type=TASK_TYPE_PLATFORM_ACTION,
        platform=str(payload.get("platform", "")),
        payload=payload,
        progress_total=1,
        priority=priority,
    )
