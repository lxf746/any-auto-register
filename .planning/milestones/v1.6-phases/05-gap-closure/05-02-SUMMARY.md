---
phase: 05-gap-closure
plan: 02
subsystem: infra
tags: [retry, backoff, dead-code, cleanup, http-client]

# Dependency graph
requires:
  - phase: 05-01
    provides: [BrowserPool factory, rate limiting, metrics integration]
provides:
  - "Dead code removed from task_scheduler.py (3 duplicate functions)"
  - "HTTPClient uses retry_with_backoff with exponential backoff + jitter"
affects: [06-next-phase]

# Tech tracking
tech-stack:
  added: []
  patterns: [retry-with-backoff integration, dead-code-cleanup]

key-files:
  created: []
  modified:
    - application/tasks/task_scheduler.py
    - core/http_client.py
    - tests/test_gap_closure_integrations.py

key-decisions:
  - "Used exponential backoff with jitter instead of linear sleep for better thundering-herd prevention"
  - "Cleaned up unused imports after dead code removal to keep file tidy"

patterns-established:
  - "retry_with_backoff as the standard retry mechanism for HTTP operations"
  - "Dead code removal: verify no imports before deleting duplicate functions"

requirements-completed: []

coverage:
  - id: D1
    description: "Dead code removed from task_scheduler.py - 3 duplicate functions (claim_next_runnable_task, mark_incomplete_tasks_interrupted, request_cancel) eliminated"
    verification:
      - kind: unit
        ref: "tests/test_gap_closure_integrations.py::TestSchedulerDeadCodeRemoved"
        status: pass
    human_judgment: false
  - id: D2
    description: "HTTPClient uses retry_with_backoff with exponential backoff and jitter instead of manual retry loop"
    verification:
      - kind: unit
        ref: "tests/test_gap_closure_integrations.py::TestHttpClientRetryIntegration"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-06-27
status: complete
---

# Phase 5 Plan 02: Dead Code Removal and Retry Integration Summary

**Dead code removed from task_scheduler.py and HTTPClient uses retry_with_backoff with exponential backoff + jitter**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-27T07:40:17Z
- **Completed:** 2026-06-27T07:44:59Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Removed 3 duplicate functions from task_scheduler.py (claim_next_runnable_task, mark_incomplete_tasks_interrupted, request_cancel + helper)
- Integrated retry_with_backoff into HTTPClient replacing manual retry loop with exponential backoff + jitter
- Added 14 new tests covering dead code removal and retry integration behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead code from task_scheduler.py** - `a2847fd` (refactor)
2. **Task 2: RED phase - failing tests** - `480a26b` (test)
3. **Task 2: GREEN phase - retry integration** - `fad8862` (feat)

## Files Created/Modified
- `application/tasks/task_scheduler.py` - Removed 3 duplicate functions, cleaned unused imports
- `core/http_client.py` - Replaced manual retry loop with retry_with_backoff (exponential + jitter)
- `tests/test_gap_closure_integrations.py` - Added 14 tests for dead code removal and retry integration

## Decisions Made
- Used `backoff_strategy="exponential"` with `jitter=True` for better thundering-herd prevention than linear sleep
- Cleaned up unused imports (Session, select, engine, ACTIVE_TASK_STATUSES, etc.) after dead code removal
- TDD approach for Task 2: wrote 9 failing tests first, then implemented

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Cleaned unused imports after dead code removal**
- **Found during:** Task 1 (dead code removal)
- **Issue:** After removing 4 functions, several imports became unused (Session, select, engine, ACTIVE_TASK_STATUSES, TERMINAL_TASK_STATUSES, etc.)
- **Fix:** Removed unused imports to keep file clean and avoid linting warnings
- **Files modified:** application/tasks/task_scheduler.py
- **Verification:** Python syntax check passes, all tests pass
- **Committed in:** a2847fd (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Cleanup necessary for code hygiene. No scope creep.

## Issues Encountered
- `session` property on HTTPClient could not be patched with `patch.object` (property has no setter) — fixed by mocking `retry_with_backoff` directly instead, which is cleaner for integration testing

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- task_scheduler.py cleaned and focused on retry logic only
- HTTPClient uses modern retry utility with exponential backoff
- All tests pass (34 total)
- Ready for next phase

---
*Phase: 05-gap-closure*
*Completed: 2026-06-27*

## Self-Check: PASSED

- All referenced files exist
- All commits verified in git log
- 34 tests passing
- No stubs or placeholders
