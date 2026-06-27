---
phase: 03-concurrent-registration
plan: 01
subsystem: database
tags: [sqlmodel, priority, alembic, task-scheduling]

# Dependency graph
requires:
  - phase: 02-connection-pooling
    provides: [database engine with connection pooling]
provides:
  - TaskModel with priority field (high/normal/low)
  - Priority-based task claiming ordering
  - PRIORITY_LEVELS constant for validation
  - Alembic migration 002 for priority column
affects: [03-02-enhanced-taskruntime]

# Tech tracking
tech-stack:
  added: []
  patterns: [priority-sort-key, python-side-sorting]

key-files:
  created:
    - alembic/versions/002_add_task_priority.py
  modified:
    - core/db/models.py
    - core/db/engine.py
    - application/tasks/task_repository.py
    - application/tasks/task_scheduler.py

key-decisions:
  - "Python-side priority sorting instead of SQL ORDER BY (alphabetical comparison breaks priority order)"
  - "PRIORITY_LEVELS as frozenset for O(1) validation"

patterns-established:
  - "Priority sort key: _priority_sort_key returns (weight, created_at) tuple for sorted()"
  - "Payload priority passthrough: create_register_task and create_platform_action_task extract priority from payload"

requirements-completed: [CONC-01, CONC-03]

coverage:
  - id: D1
    description: "TaskModel with priority field (high/normal/low) and database migration"
    requirement: CONC-03
    verification:
      - kind: unit
        ref: "python3 -c 'from core.db.models import TaskModel, PRIORITY_LEVELS; assert TaskModel(id=\"x\", priority=\"high\").priority == \"high\"'"
        status: pass
    human_judgment: false
  - id: D2
    description: "Priority-based task claiming ordering (high > normal > low, FIFO within same priority)"
    requirement: CONC-01
    verification:
      - kind: unit
        ref: "python3 -c 'from application.tasks.task_repository import _priority_sort_key; from core.db.models import TaskModel; from datetime import datetime; tasks=[TaskModel(id=\"1\",priority=\"low\",created_at=datetime(2026,1,1)),TaskModel(id=\"2\",priority=\"high\",created_at=datetime(2026,1,2)),TaskModel(id=\"3\",priority=\"normal\",created_at=datetime(2026,1,1))]; assert [t.id for t in sorted(tasks,key=_priority_sort_key)]==[\"2\",\"3\",\"1\"]'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Task serialization includes priority field in API responses"
    requirement: CONC-03
    verification:
      - kind: unit
        ref: "python3 -c 'from application.tasks.task_repository import serialize_task; from core.db.models import TaskModel; assert serialize_task(TaskModel(id=\"x\",priority=\"high\"))[\"priority\"]==\"high\"'"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-06-27
status: complete
---

# Phase 3 Plan 01: Priority Model & Priority-Based Claiming Summary

**TaskModel.priority field with high/normal/low levels, priority-based claiming ordering across task_repository and task_scheduler, Alembic migration with index**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-27T06:54:02Z
- **Completed:** 2026-06-27T06:56:15Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- TaskModel has `priority: str = Field(default="normal", index=True)` with PRIORITY_LEVELS validation
- claim_next_runnable_task orders by priority (high > normal > low) then created_at FIFO
- Both task_repository and task_scheduler claiming logic synchronized with same priority ordering
- Alembic migration 002 adds priority column with server_default "normal" and index
- SQLite compatibility via _ensure_column in engine.py init_db()

## Task Commits

Each task was committed atomically:

1. **Task 1: Add priority field to TaskModel and Alembic migration** - `9e5d597` (feat)
2. **Task 2: Priority-based task claiming and serialization** - `a4bc696` (feat)

## Files Created/Modified

- `core/db/models.py` - Added PRIORITY_LEVELS constant and priority field to TaskModel
- `core/db/engine.py` - Added _ensure_column call for priority column (SQLite compat)
- `alembic/versions/002_add_task_priority.py` - Migration: add priority column + index
- `application/tasks/task_repository.py` - Priority sort key, priority-aware claiming, create_task with priority param, serialize_task includes priority
- `application/tasks/task_scheduler.py` - Synchronized priority ordering in claim_next_runnable_task

## Decisions Made

- Used Python-side priority sorting instead of SQL ORDER BY because alphabetical comparison would order "high" < "low" < "normal" (wrong priority order)
- PRIORITY_LEVELS defined as frozenset for O(1) validation lookup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Priority model foundation complete for Plan 02 (Enhanced TaskRuntime)
- Ready for heapq-based priority dispatch in TaskRuntime
- Resource monitoring and dynamic throttling can build on priority infrastructure

---
*Phase: 03-concurrent-registration*
*Completed: 2026-06-27*
