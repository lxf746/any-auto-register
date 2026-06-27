"""Task orchestration and persistence helpers."""
from __future__ import annotations

from application.tasks.task_repository import (
    ACTIVE_TASK_STATUSES,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_CANCEL_REQUESTED,
    TASK_STATUS_CLAIMED,
    TASK_STATUS_FAILED,
    TASK_STATUS_INTERRUPTED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCEEDED,
    TERMINAL_TASK_STATUSES,
    TASK_TYPE_ACCOUNT_CHECK,
    TASK_TYPE_ACCOUNT_CHECK_ALL,
    TASK_TYPE_PLATFORM_ACTION,
    TASK_TYPE_REGISTER,
    append_task_event,
    claim_next_runnable_task,
    create_account_check_all_task,
    create_account_check_task,
    create_platform_action_task,
    create_register_task,
    create_task,
    get_task,
    list_task_events,
    list_tasks,
    mark_incomplete_tasks_interrupted,
    mutate_task,
    request_cancel,
    save_task_log,
    serialize_event,
    serialize_task,
    task_lock,
)

from application.tasks.task_runner import (
    TaskLogger,
    execute_task,
)

from application.tasks.task_scheduler import (
    schedule_retry,
)

__all__ = [
    # Constants
    "ACTIVE_TASK_STATUSES",
    "TASK_STATUS_CANCELLED",
    "TASK_STATUS_CANCEL_REQUESTED",
    "TASK_STATUS_CLAIMED",
    "TASK_STATUS_FAILED",
    "TASK_STATUS_INTERRUPTED",
    "TASK_STATUS_PENDING",
    "TASK_STATUS_RUNNING",
    "TASK_STATUS_SUCCEEDED",
    "TERMINAL_TASK_STATUSES",
    "TASK_TYPE_ACCOUNT_CHECK",
    "TASK_TYPE_ACCOUNT_CHECK_ALL",
    "TASK_TYPE_PLATFORM_ACTION",
    "TASK_TYPE_REGISTER",
    # Repository
    "append_task_event",
    "claim_next_runnable_task",
    "create_account_check_all_task",
    "create_account_check_task",
    "create_platform_action_task",
    "create_register_task",
    "create_task",
    "get_task",
    "list_task_events",
    "list_tasks",
    "mark_incomplete_tasks_interrupted",
    "mutate_task",
    "request_cancel",
    "save_task_log",
    "serialize_event",
    "serialize_task",
    "task_lock",
    # Runner
    "TaskLogger",
    "execute_task",
    # Scheduler
    "schedule_retry",
]
