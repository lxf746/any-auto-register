"""Persistent task runtime for single-process execution."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import threading
import time

from application.tasks import claim_next_runnable_task, execute_task, mark_incomplete_tasks_interrupted

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TaskWorkerState:
    thread: threading.Thread
    platform: str = ""
    account_keys: set[str] = field(default_factory=set)


class TaskRuntime:
    def __init__(self, *, max_parallel_tasks: int = 3, max_parallel_per_platform: int = 1, poll_interval: float = 0.5):
        self.max_parallel_tasks = max_parallel_tasks
        self.max_parallel_per_platform = max_parallel_per_platform
        self.poll_interval = poll_interval
        self._running = False
        self._dispatcher: threading.Thread | None = None
        self._workers: dict[str, TaskWorkerState] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            mark_incomplete_tasks_interrupted()
            self._dispatcher = threading.Thread(target=self._loop, daemon=True, name="task-runtime")
            self._dispatcher.start()
            logger.info("Started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        logger.info("Stopping")

    def wake_up(self) -> None:
        # Polling loop wakes quickly already; this method exists as an explicit runtime hook.
        return

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
            while available_slots > 0 and self._running:
                task_info = claim_next_runnable_task(
                    running_platform_counts=running_platform_counts,
                    busy_account_keys=busy_account_keys,
                    max_parallel_per_platform=self.max_parallel_per_platform,
                )
                if not task_info:
                    break
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
                    )
                    if task_info.get("platform"):
                        running_platform_counts[str(task_info["platform"])] = running_platform_counts.get(str(task_info["platform"]), 0) + 1
                    busy_account_keys.update(set(task_info.get("account_keys") or []))
                worker.start()
                available_slots -= 1
            time.sleep(self.poll_interval)
        self._reap_workers()

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
