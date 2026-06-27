"""Persistent task runtime for single-process execution."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
import logging
import threading
import time

from application.tasks import claim_next_runnable_task, execute_task, mark_incomplete_tasks_interrupted
from core.db.engine import resource_monitor, get_resource_metrics

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TaskWorkerState:
    thread: threading.Thread
    platform: str = ""
    account_keys: set[str] = field(default_factory=set)
    priority: str = "normal"


class TaskRuntime:
    def __init__(self, *, max_parallel_tasks: int = 3, max_parallel_per_platform: int = 1, poll_interval: float = 0.5):
        self.max_parallel_tasks = max_parallel_tasks
        self.max_parallel_per_platform = max_parallel_per_platform
        self.poll_interval = poll_interval
        self._running = False
        self._dispatcher: threading.Thread | None = None
        self._workers: dict[str, TaskWorkerState] = {}
        self._lock = threading.Lock()
        self._started_at: float = 0.0

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._started_at = time.monotonic()
            mark_incomplete_tasks_interrupted()
            self._dispatcher = threading.Thread(target=self._loop, daemon=True, name="task-runtime")
            self._dispatcher.start()
            logger.info("Started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        logger.info("Stopping")
        if self._dispatcher:
            self._dispatcher.join(timeout=5)
        with self._lock:
            workers = dict(self._workers)
        for worker in workers.values():
            if worker.thread and worker.thread.is_alive():
                worker.thread.join(timeout=5)

    def wake_up(self) -> None:
        # Polling loop wakes quickly already; this method exists as an explicit runtime hook.
        return

    @staticmethod
    def _pending_task_sort_key(task_info: dict) -> tuple[int, str]:
        """Sort key for priority-based dispatch: high(0) > normal(1) > low(2), then FIFO by id."""
        priority_order = {"high": 0, "normal": 1, "low": 2}
        return (priority_order.get(task_info.get("priority", "normal"), 1), task_info.get("id", ""))

    def _loop(self) -> None:
        while self._running:
            self._reap_workers()
            with self._lock:
                available_slots = self.max_parallel_tasks - len(self._workers)
                running_platform_counts: dict[str, int] = {}
                busy_account_keys: set[str] = set()
                for state in self._workers.values():
                    if state.platform:
                        running_platform_counts[state.platform] = running_platform_counts.get(state.platform, 0) + 1
                    busy_account_keys.update(state.account_keys)
            # Apply resource-aware throttling (min 1 slot to prevent deadlock)
            throttle = resource_monitor.get_throttle_factor()
            if throttle < 1.0:
                available_slots = max(1, int(available_slots * throttle))
            # Collect claimable tasks into a batch for priority sorting
            claimable_tasks: list[dict] = []
            while available_slots > len(claimable_tasks) and self._running:
                task_info = claim_next_runnable_task(
                    running_platform_counts=running_platform_counts,
                    busy_account_keys=busy_account_keys,
                    max_parallel_per_platform=self.max_parallel_per_platform,
                )
                if not task_info:
                    break
                claimable_tasks.append(task_info)
                # Update tracking for next claim
                platform = str(task_info.get("platform", "") or "")
                if platform:
                    running_platform_counts[platform] = running_platform_counts.get(platform, 0) + 1
                busy_account_keys.update(set(task_info.get("account_keys") or []))
            # Sort collected tasks by priority (high first)
            claimable_tasks.sort(key=TaskRuntime._pending_task_sort_key)
            # Dispatch in sorted order
            for task_info in claimable_tasks:
                task_id = task_info["id"]
                worker = threading.Thread(
                    target=self._run_task,
                    args=(task_id,),
                    daemon=True,
                    name=f"task-worker-{task_id}",
                )
                with self._lock:
                    self._workers[task_id] = TaskWorkerState(
                        thread=worker,
                        platform=str(task_info.get("platform", "") or ""),
                        account_keys=set(task_info.get("account_keys") or []),
                        priority=task_info.get("priority", "normal"),
                    )
                worker.start()
            time.sleep(self.poll_interval)
        self._reap_workers()

    def get_runtime_stats(self) -> dict:
        """Return current runtime statistics including running count, per-priority breakdown, and resource metrics."""
        with self._lock:
            running_count = len(self._workers)
            per_platform_counts: dict[str, int] = {}
            per_priority_counts: dict[str, int] = {}
            for state in self._workers.values():
                if state.platform:
                    per_platform_counts[state.platform] = per_platform_counts.get(state.platform, 0) + 1
                per_priority_counts[state.priority] = per_priority_counts.get(state.priority, 0) + 1
        uptime = time.monotonic() - self._started_at if self._started_at else 0.0
        resource_metrics = get_resource_metrics()
        return {
            "running_count": running_count,
            "max_parallel_tasks": self.max_parallel_tasks,
            "per_platform_counts": per_platform_counts,
            "per_priority_counts": per_priority_counts,
            "uptime": uptime,
            **resource_metrics,
        }

    def _run_task(self, task_id: str) -> None:
        try:
            execute_task(task_id)
        finally:
            with self._lock:
                self._workers.pop(task_id, None)

    def _reap_workers(self) -> None:
        with self._lock:
            finished = [task_id for task_id, worker in self._workers.items() if not worker.thread.is_alive()]
            for task_id in finished:
                self._workers.pop(task_id, None)


task_runtime = TaskRuntime()
